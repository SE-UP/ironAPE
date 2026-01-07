import json
from rdflib import RDF, RDFS, BNode, Graph
from semantikon import ontology as onto


query = """
SELECT ?software ?label ?identifier ?uri WHERE {
    ?software a iao:0000591 .
    ?software rdfs:label ?label .
    ?software iao:0000235 ?identifier_bnode .
    ?identifier_bnode a iao:0020000 .
    ?identifier_bnode rdf:value ?identifier .
    OPTIONAL {
        ?software iao:0000136 ?uri .
    }
}"""


def knowledge_graph_to_ape(graph):
    all_data = []
    for entry in graph.query(query):
        data = {
            "label": entry[1].toPython(),
            "id": entry[2].toPython(),
            "taxonomyOperations": (
                [BNode(data["label"])] if entry[3] is None else [entry[3]]
            ),
        }
        software = entry[0]
        no_uri = False
        inputs = []
        outputs = []
        for bnode in graph.objects(software, onto.SNS.has_parameter_specification):
            is_input = (
                RDF.type,
                onto.SNS.input_specification,
            ) in graph.predicate_objects(bnode)
            if list(graph.objects(bnode, onto.SNS.is_about)):
                io = [
                    list(graph.objects(bnode, onto.SNS.has_parameter_position))[
                        0
                    ].toPython(),
                    list(graph.objects(bnode, onto.SNS.is_about))[0].toPython(),
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
