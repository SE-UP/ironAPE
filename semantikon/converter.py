import json
from rdflib import RDF, RDFS, OWL, BNode, Graph
from semantikon import ontology as onto

node_query = """
PREFIX pmd: <https://w3id.org/pmd/co/PMD_>
PREFIX ex: <http://example.org/>

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


def knowledge_graph_to_ape(graph, ontology: Graph | None = None):
    all_data = []
    for entry in graph.query(node_query):
        data = {
            "label": entry[1].toPython(),
            "id": entry[2].toPython(),
            "taxonomyOperations": (
                [BNode(entry[1].toPython())] if entry[3] is None else [entry[3]]
            ),
        }
        software = entry[0]
        no_uri = False
        inputs = []
        outputs = []
        for bnode in graph.objects(software, onto.SNS.has_part):
            is_input = (
                RDF.type,
                onto.SNS.input_specification,
            ) in graph.predicate_objects(bnode)
            if list(graph.objects(bnode, onto.SNS.is_about)):
                is_about_node = list(graph.objects(bnode, onto.SNS.is_about))[0]
                is_about_class = list(graph.objects(is_about_node, RDF.type))[0]
                io = [
                    list(graph.objects(bnode, onto.SNS.has_parameter_position))[
                        0
                    ].toPython(),
                    is_about_class.toPython(),
                ]
                if is_input:
                    inputs.append(io)
                else:
                    outputs.append(io)
            else:
                no_uri = True
                break
        if not no_uri:
            data["inputs"] = [
                {"Type": [x]} for _, x in sorted(inputs, key=lambda pair: pair[0])
            ]
            data["outputs"] = [
                {"Type": [x]} for _, x in sorted(outputs, key=lambda pair: pair[0])
            ]
            all_data.append(data)
    return all_data


graph = Graph()
graph.parse("example/example_function_ontology.ttl")
all_data = knowledge_graph_to_ape(graph)
with open("example/tool_annotations.json", "w") as f:
    json.dump({"functions": all_data}, f, indent=4)
