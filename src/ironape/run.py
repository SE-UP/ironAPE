import json
import os
import tempfile
import subprocess
from rdflib import Graph
from ironape.converter import knowledge_graph_to_ape
from ironape.config import Config



def run_ape(
    graph: Graph,
    inputs: list[dict[str, list[str]]],
    outputs: list[dict[str, list[str]]],
    executable_path: str | None = None,
    executable: str = "APE-2.6.0-executable.jar",
):
    if executable_path is None:
        executable_path = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(executable):
        executable = os.path.join(executable_path, executable)
    all_data, g_onto = knowledge_graph_to_ape(graph)

    with tempfile.TemporaryDirectory() as temp_dir:
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
