import json
from typing import Any, cast

from cwl_utils import parser
from rdflib import OWL, RDF, RDFS, Graph, URIRef
from rdflib.namespace import split_uri
from semantikon import cwl, ontology
from semantikon import ontology as onto  # external semantikon package

node_query = """
PREFIX pmd: <https://w3id.org/pmd/co/PMD_>
PREFIX iao: <http://purl.obolibrary.org/obo/IAO_>

SELECT ?software ?label ?identifier ?uri WHERE {
    ?software a pmd:0000010 .
    ?software iao:0000235 ?label_node .
    ?label_node a pmd:0000100 .
    ?label_node pmd:0000006 ?label .
    ?software iao:0000235 ?identifier_bnode .
    ?identifier_bnode a iao:0020000 .
    ?identifier_bnode pmd:0000006 ?identifier .
    OPTIONAL {
        ?software iao:0000136 ?uri_bnode .
        ?uri_bnode a ?uri .
    }
}"""


io_query = """PREFIX bfo: <http://purl.obolibrary.org/obo/BFO_>
PREFIX pmd: <https://w3id.org/pmd/co/PMD_>
PREFIX iao: <http://purl.obolibrary.org/obo/IAO_>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?bnode ?parameter_position ?is_about_class ?is_input
WHERE {
  ?software bfo:0000051 ?bnode .

  OPTIONAL {
    ?bnode rdf:type pmd:0000014 .
    BIND(true AS ?is_input)
  }
  FILTER(!BOUND(?is_input) || ?is_input = true)

  OPTIONAL {
    ?bnode rdf:type ?is_about_node .
    ?is_about_node rdf:type owl:Restriction .
    ?is_about_node owl:allValuesFrom ?is_about_class .
    ?is_about_node owl:onProperty iao:0000136 .
  }

  # Get the parameter position of the blank node
  OPTIONAL {
    ?bnode pmd:0001857 ?parameter_position .
  }
}"""


def initialize_ontology() -> Graph:
    """Initialize the ontology graph with base classes."""
    g_onto = Graph()
    g_onto.add((onto.BASE["Tool"], RDF.type, OWL.Class))
    g_onto.add((onto.BASE["Type"], RDF.type, OWL.Class))
    g_onto.add((onto.BASE["Format"], RDF.type, OWL.Class))
    return g_onto


def process_io_query(graph: Graph, software: Any) -> tuple[list, list, bool]:
    """Process the IO query for a given software."""
    inputs, outputs = [], []
    no_uri = False
    for io_entry in graph.query(io_query, initBindings={"software": software}):
        is_input = io_entry[3].toPython() if io_entry[3] is not None else False
        if io_entry[2] is not None:
            io = [io_entry[1].toPython(), io_entry[2]]
            if is_input:
                inputs.append(io)
            else:
                outputs.append(io)
        else:
            no_uri = True
            break
    return inputs, outputs, no_uri


def add_to_ontology(g_onto: Graph, inputs: list, outputs: list, uri: Any) -> None:
    """Add inputs and outputs to the ontology graph."""
    g_onto.add((uri, RDFS.subClassOf, onto.BASE["Tool"]))
    g_onto.add((uri, RDF.type, OWL.Class))
    for inp in inputs:
        g_onto.add((inp[1], RDFS.subClassOf, onto.BASE["Type"]))
        g_onto.add((inp[1], RDF.type, OWL.Class))
    for out in outputs:
        g_onto.add((out[1], RDFS.subClassOf, onto.BASE["Type"]))
        g_onto.add((out[1], RDF.type, OWL.Class))


def _arg_to_cwl_input(
    cwl_module: Any, arg: dict[str, Any], position: int
) -> parser.CommandInputParameter:
    """
    Convert function input argument metadata into a CWL input parameter.

    Args:
        cwl_module: The versioned ``cwl_utils.parser`` submodule to build
            objects with (e.g. ``cwl_utils.parser.cwl_v1_2``).
        arg (dict[str, Any]): Argument metadata as produced by
            ``ontology._graph_to_function``.
        position (int): Fallback input/argument position if none is recorded.

    Returns:
        parser.CommandInputParameter: The resulting CWL input parameter.
    """
    kwargs: dict[str, Any] = {
        "id": f"input_{position + 1}",
        "type_": cwl._infer_cwl_type(arg),
        "inputBinding": cwl_module.CommandLineBinding(
            position=arg.get("position", position)
        ),
    }
    if "default" in arg:
        kwargs["default"] = arg["default"]
    return cwl_module.CommandInputParameter(**kwargs)


def _arg_to_cwl_output(
    cwl_module: Any, arg: dict[str, Any], position: int
) -> parser.CommandOutputParameter:
    """
    Convert function output argument metadata into a CWL output parameter.

    Args:
        cwl_module: The versioned ``cwl_utils.parser`` submodule to build
            objects with (e.g. ``cwl_utils.parser.cwl_v1_2``).
        arg (dict[str, Any]): Argument metadata as produced by
            ``ontology._graph_to_function``.
        position (int): Fallback output position if none is recorded.

    Returns:
        parser.CommandOutputParameter: The resulting CWL output parameter.
    """
    return cwl_module.CommandOutputParameter(
        id=f"output_{position + 1}",
        type_=cwl._infer_cwl_type(arg),
    )


def _get_function_name(g: Graph, f_node: URIRef) -> str:
    for denoted_by in g.objects(f_node, ontology.SNS.denoted_by):
        if (denoted_by, RDF.type, ontology.SNS.function_name) in g:
            return g.value(denoted_by, ontology.SNS.has_value).toPython()
    raise ValueError(f"Function node {f_node} has no identifier in the graph.")


def knowledge_graph_to_cwl(
    graph: Graph, f_node: URIRef | None = None, cwl_version: str = "v1.2"
) -> parser.CommandLineTool:
    """
    Convert a function stored in a knowledge graph into an in-memory CWL
    ``CommandLineTool`` object.

    The knowledge graph is expected to have been produced (at least in part)
    by ``semantikon.ontology.function_to_knowledge_graph``, i.e. it must
    contain a node of type ``SNS.workflow_function`` describing the function's
    inputs and outputs.

    Args:
        graph (rdflib.Graph): Knowledge graph containing the function
            description.
        f_node (rdflib.URIRef | None): URI of the function node to convert.
            If ``None``, the graph must contain exactly one node of type
            ``SNS.workflow_function``.
        cwl_version (str): CWL schema version to target, e.g. ``"v1.0"``,
            ``"v1.1"`` or ``"v1.2"``.

    Returns:
        parser.CommandLineTool: The resulting CWL tool description.
    """
    if f_node is None:
        candidates = list(graph.subjects(RDF.type, ontology.SNS.workflow_function))
        if len(candidates) != 1:
            raise ValueError(
                "f_node must be provided explicitly unless the graph contains "
                f"exactly one function node (found {len(candidates)})."
            )
        f_node = cast(URIRef, candidates[0])

    data = ontology._graph_to_function(graph, f_node)
    cwl_module = getattr(parser, f"cwl_{cwl_version.replace('.', '_')}")

    inputs = [
        _arg_to_cwl_input(cwl_module, arg, position)
        for position, arg in enumerate(data["input_args"])
    ]
    outputs = [
        _arg_to_cwl_output(cwl_module, arg, position)
        for position, arg in enumerate(data["output_args"])
    ]

    return cwl_module.CommandLineTool(
        id=_get_function_name(graph, f_node).replace(":", "_"),
        inputs=inputs,
        outputs=outputs,
        doc=data["data"].get("docstring") or None,
        cwlVersion=cwl_version,
    )


def knowledge_graph_to_ape(graph: Graph) -> tuple[list[dict[str, Any]], Graph]:
    """Convert a knowledge graph to APE format."""
    g_onto = initialize_ontology()
    all_data = []

    for entry in graph.query(node_query):
        inputs, outputs, no_uri = process_io_query(graph, entry[0])
        if not no_uri:
            uri = onto.BASE[entry[1].toPython()] if entry[3] is None else entry[3]
            add_to_ontology(g_onto, inputs, outputs, uri)
            data = {
                "label": entry[1].toPython(),
                "id": entry[2].toPython(),
                "taxonomyOperations": [split_uri(uri)[1]],
                "inputs": [
                    {"Type": [split_uri(x)[1]]}
                    for _, x in sorted(inputs, key=lambda pair: pair[0])
                ],
                "outputs": [
                    {"Type": [split_uri(x)[1]]}
                    for _, x in sorted(outputs, key=lambda pair: pair[0])
                ],
                "implementation": {"cwl_reference": entry[1].toPython() + ".cwl"},
            }
            all_data.append(data)

    return all_data, g_onto


if __name__ == "__main__":
    graph = Graph()
    graph.parse("examples/example_function_ontology.ttl")
    all_data, g_onto = knowledge_graph_to_ape(graph)

    with open("examples/tool_annotations.json", "w") as f:
        json.dump({"functions": all_data}, f, indent=4)

    with open("examples/taxonomy.owl", "w") as f:
        f.write(g_onto.serialize(format="xml"))
