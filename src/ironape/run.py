import contextlib
import importlib
import json
import os
import re
import networkx as nx
from semantikon.flowrep_dict import _flowrep_recipe_from_callable
import rdflib
import subprocess
import tempfile
from pathlib import Path

from cwl_utils import parser
from rdflib import Graph
from semantikon import ontology
from semantikon.flowrep_to_networkx import Input, Node, Output
from semantikon.cwl import save_cwl_file
from semantikon.kg_to_flowrep import _networkx_to_flowrep, _graph_to_function, Node, Input, Output


from ironape.config import Config
from ironape.converter import knowledge_graph_to_ape, knowledge_graph_to_cwl


def run_ape(
    graph: Graph,
    inputs: list[dict[str, list[str]]],
    outputs: list[dict[str, list[str]]],
    executable_path: str | None = None,
    executable: str = "APE-2.6.0-executable.jar",
    working_directory: str | None = None,
) -> tuple[str, str]:
    """
    Run the APE tool with the given knowledge graph, inputs, and outputs.

    Args:
        graph (Graph): The knowledge graph to be used.
        inputs (list[dict[str, list[str]]]): List of input specifications.
        outputs (list[dict[str, list[str]]]): List of output specifications.
        executable_path (str | None): Path to the APE executable. If None, uses the current directory.
        executable (str): Name of the APE executable file.
        working_directory (str | None): Directory to use for temporary files. If None, a temporary directory is created.

    Returns:
        tuple[str, str]: A tuple containing the standard output and standard error from the APE execution.
    """
    if executable_path is None:
        executable_path = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(executable):
        executable = os.path.join(executable_path, executable)
    all_data, g_onto = knowledge_graph_to_ape(graph)

    if working_directory is None:
        dir_context = tempfile.TemporaryDirectory()
    else:
        os.makedirs(working_directory, exist_ok=True)
        dir_context = contextlib.nullcontext(os.path.abspath(working_directory))

    with dir_context as temp_dir:
        tool_annotation_path = os.path.join(temp_dir, "tool_annotations.json")
        taxonomy_path = os.path.join(temp_dir, "taxonomy.owl")
        constraints_path = os.path.join(temp_dir, "constraints.json")
        config_path = os.path.join(temp_dir, "config.json")
        config = Config(
            ontology_path=taxonomy_path,
            ontologyPrefixIRI="http://pyiron.org/ontology/",
            tool_annotations_path=tool_annotation_path,
            constraints_path=constraints_path,
            solutions_dir_path=".",
            inputs=inputs,
            outputs=outputs,
        )

        with open(tool_annotation_path, "w") as f:
            json.dump({"functions": all_data}, f, indent=4)
        with open(taxonomy_path, "w") as f:
            f.write(g_onto.serialize(format="xml"))
        with open(constraints_path, "w") as f:
            json.dump({"constraints": []}, f, indent=4)
        with open(config_path, "w") as f:
            json.dump(config.model_dump(), f, indent=4)
        output = subprocess.run(
            ["java", "-jar", executable, config_path],
            capture_output=True,
            text=True,
        )
    return output.stdout, output.stderr


def _get_function_name(g, f_node):
    for denoted_by in g.objects(f_node, ontology.SNS.denoted_by):
        if (denoted_by, rdflib.RDF.type, ontology.SNS.function_name) in g:
            return g.value(denoted_by, ontology.SNS.has_value).toPython()
    raise ValueError(f"No function name found for node {f_node}")



def serialize_and_convert_to_networkx(uri: str | Path) -> ontology.SemantikonDiGraph:
    """
    Parse a CWL document and build a knowledge graph.

    Args:
        uri (str | Path): Path or URI to the CWL file.

    Returns:
        ontology.SemantikonDiGraph: A directed graph representing the workflow
            structure, with nodes for inputs, outputs, and steps, and edges
            representing data flow between them.
    """
    wf = parser.load_document_by_uri(uri)
    return _add_node(wf)


def _get_name(tag: str) -> str:
    """
    Extract the local name from a CWL identifier URI.

    CWL identifiers are typically full URIs or fragment identifiers of the form
    ``file:///path/to/file.cwl#local_name``. This function returns the part after
    the ``#`` character, or the full string if no ``#`` is present.

    Args:
        tag (str): A CWL identifier string.

    Returns:
        str: The local name extracted from the identifier.
    """
    return tag.split("#")[-1]


def _get_port_name(tag: str) -> str:
    """Return the bare port name, dropping any process-id prefix (``tool/port``)."""
    return _get_name(tag).split("/")[-1]


def _resolve_port(port: str, kind: str, names: list[str]) -> str:
    """
    Map an APE-style step port (``<tool>_in_N`` / ``<tool>_out_N``) onto the
    N-th port name of the referenced process. Other names are kept as is.
    """
    match = re.search(rf"_{kind}_(\d+)$", port)
    if match is not None and port not in names:
        index = int(match.group(1)) - 1
        if 0 <= index < len(names):
            return names[index]
    return port


def _add_node(
    wf: parser.CommandLineTool | parser.Workflow,
    G: ontology.SemantikonDiGraph | None = None,
    prefix: Node | None = None,
) -> ontology.SemantikonDiGraph:
    """
    Recursively add nodes and edges for a CWL process to the knowledge graph.

    For a ``CommandLineTool``, input and output nodes are added. For a
    ``Workflow``, step nodes are also added along with edges representing the
    data flow between steps.

    Args:
        wf (parser.CommandLineTool | parser.Workflow): The CWL process to add
            to the graph.
        G (ontology.SemantikonDiGraph | None): The graph to populate. If
            ``None``, a new graph is created using the workflow's filename as
            the prefix.
        prefix (str | None): The node name prefix. If ``None``, derived from
            the CWL filename (without the ``.cwl`` extension).

    Returns:
        ontology.SemantikonDiGraph: The populated knowledge graph.
    """
    if prefix is None:
        prefix = Node(name=wf.id.split("/")[-1].replace(".cwl", ""))
    if G is None:
        G = ontology.SemantikonDiGraph(prefix=str(prefix))

    for position, inp in enumerate(wf.inputs):
        inp_node = Input(node=prefix, port=_get_port_name(inp.id))
        inp_position = position
        if inp.inputBinding is not None and inp.inputBinding.position is not None:
            inp_position = inp.inputBinding.position
        G.add_node(inp_node, position=inp_position)
        G.add_edge(inp_node, prefix)

    for position, out in enumerate(wf.outputs):
        out_node = Output(node=prefix, port=_get_port_name(out.id))
        G.add_node(out_node, position=position)
        G.add_edge(prefix, out_node)

    if isinstance(wf, parser.CommandLineTool | parser.WorkflowStep):
        return G

    _step_outputs: dict[str, list[str]] = {}
    for step in wf.steps:
        _step_outputs[_get_name(step.id)] = [
            _get_port_name(o.id)
            for o in parser.load_document_by_uri(step.run).outputs
        ]
    for step in wf.steps:
        node = Node(owner=prefix, name=_get_name(step.id))
        run_doc = parser.load_document_by_uri(step.run)
        node_type = "workflow" if isinstance(run_doc, parser.Workflow) else "atomic"
        G.add_node(node, type=node_type)
        run_inputs = [_get_port_name(i.id) for i in run_doc.inputs]
        run_outputs = [_get_port_name(o.id) for o in run_doc.outputs]
        for inp in step.in_:
            n, p = _get_name(inp.id).split("/")
            p = _resolve_port(p, "in", run_inputs)
            dest = Input(node=Node(owner=prefix, name=n), port=p)
            s = _get_name(inp.source)
            if "/" in s:
                n, p = s.split("/")
                p = _resolve_port(p, "out", _step_outputs.get(n, []))
                G.add_edge(Output(node=Node(owner=prefix, name=n), port=p), dest)
            else:
                G.add_edge(Input(node=prefix, port=s), dest)
            G.add_edge(dest, node)
        for out in step.out:
            out_name = _get_name(out)
            if "/" in out_name:
                n, p = out_name.split("/")
                p = _resolve_port(p, "out", run_outputs)
                G.add_edge(node, Output(node=Node(owner=prefix, name=n), port=p))
            else:
                out_name = _resolve_port(out_name, "out", run_outputs)
                G.add_edge(node, Output(node=node, port=out_name))
        G = _add_node(run_doc, G, prefix=node)

    for out in wf.outputs:
        n, p = _get_name(out.outputSource).split("/")
        p = _resolve_port(p, "out", _step_outputs.get(n, []))
        G.add_edge(
            Output(node=Node(owner=prefix, name=n), port=p),
            Output(node=prefix, port=_get_name(out.id)),
        )
    return G


def _port_relabeling(G: nx.DiGraph, node: Node, f: dict) -> dict:
    """Map positional CWL port names (``input_1``) to the function's argument names."""
    mapping = {}
    func = getattr(
        importlib.import_module(f["data"]["module"]),
        f["data"]["qualname"],
    )
    recipe_outputs = _flowrep_recipe_from_callable(func, node_type="atomic").outputs
    output_names = {a["position"]: recipe_outputs[a["position"]] for a in f["output_args"]}
    for port_cls, by_position in (
        (Input, {a["position"]: a["arg"] for a in f["input_args"]}),
        (Output, output_names),
    ):
        for n in G.nodes:
            if isinstance(n, port_cls) and n.node == node:
                new = by_position.get(G.nodes[n]["position"])
                if new is not None and new != n.port:
                    mapping[n] = port_cls(node=node, port=new)
    return mapping


def _terminal_relabeling(G: nx.DiGraph, root: Node) -> dict:
    """
    Name the workflow-level inputs/outputs after the node ports they are wired
    to. On name clashes, a numeric suffix is appended.
    """
    mapping: dict = {}
    used: set[str] = set()

    def _unique(name: str) -> str:
        candidate, i = name, 1
        while candidate in used:
            i += 1
            candidate = f"{name}_{i}"
        used.add(candidate)
        return candidate

    ports = sorted(
        (n for n in G.nodes if isinstance(n, Input | Output) and n.node == root),
        key=lambda n: G.nodes[n]["position"],
    )
    for n in ports:
        if isinstance(n, Input):
            linked = [m for m in G.successors(n) if isinstance(m, Input) and m.node != root]
        else:
            linked = [m for m in G.predecessors(n) if isinstance(m, Output) and m.node != root]
        new = _unique(linked[0].port if linked else n.port)
        if new != n.port:
            mapping[n] = type(n)(node=root, port=new)
    return mapping


def cwl_to_flowrep(file_name: str, g: Graph) -> None:
    function_dict = {}
    for f_node in g.subjects(rdflib.RDF.type, ontology.SNS.workflow_function):
        tool = knowledge_graph_to_cwl(g, f_node)
        function_id = _get_function_name(g, f_node)
        save_cwl_file(tool, str(Path(file_name).parent / f"{function_id}.cwl"))
        function_dict[function_id] = f_node

    G = serialize_and_convert_to_networkx(file_name)

    for node in G.nodes:
        if isinstance(node, Node) and node.owner is None:
            G.name = node.name

    mapping: dict = {}
    for n in list(G.nodes):
        if isinstance(n, Node) and G.nodes[n].get("type", "") == "atomic":
            f = _graph_to_function(g, function_dict[n.name.rsplit("_", 1)[0]])
            G.nodes[n]["function"] = f["data"]
            mapping.update(_port_relabeling(G, n, f))
    nx.relabel_nodes(G, mapping, copy=False)
    nx.relabel_nodes(G, _terminal_relabeling(G, Node(G.name)), copy=False)

    return _networkx_to_flowrep(G)
