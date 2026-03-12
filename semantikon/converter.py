import json
from rdflib import RDF, RDFS, OWL, BNode, Graph
from rdflib.namespace import split_uri
from semantikon import ontology as onto

node_query = """
PREFIX pmd: <https://w3id.org/pmd/co/PMD_>

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


def knowledge_graph_to_ape(graph: Graph) -> list:
    g_onto = Graph()
    g_onto.add((onto.BASE["Tool"], RDF.type, OWL.Class))
    g_onto.add((onto.BASE["Type"], RDF.type, OWL.Class))
    g_onto.add((onto.BASE["Format"], RDF.type, OWL.Class))
    all_data = []
    for entry in graph.query(node_query):
        uri = onto.BASE[entry[1].toPython()] if entry[3] is None else entry[3]
        data = {
            "label": entry[1].toPython(),
            "id": entry[2].toPython(),
            "taxonomyOperations": ([split_uri(uri)[1]]),
        }
        g_onto.add((uri, RDFS.subClassOf, onto.BASE["Tool"]))
        g_onto.add((uri, RDF.type, OWL.Class))
        software = entry[0]
        no_uri = False
        inputs = []
        outputs = []
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
        if not no_uri:
            data["inputs"] = [
                {"Type": [split_uri(x)[1]]}
                for _, x in sorted(inputs, key=lambda pair: pair[0])
            ]
            data["outputs"] = [
                {"Type": [split_uri(x)[1]]}
                for _, x in sorted(outputs, key=lambda pair: pair[0])
            ]
            for inp in inputs:
                g_onto.add((inp[1], RDFS.subClassOf, onto.BASE["Type"]))
                g_onto.add((inp[1], RDF.type, OWL.Class))
            for out in outputs:
                g_onto.add((out[1], RDFS.subClassOf, onto.BASE["Type"]))
                g_onto.add((out[1], RDF.type, OWL.Class))
            all_data.append(data)
    return all_data, g_onto


if __name__ == "__main__":
    graph = Graph()
    graph.parse("example/example_function_ontology.ttl")
    all_data, g_onto = knowledge_graph_to_ape(graph)
    with open("example/tool_annotations.json", "w") as f:
        json.dump({"functions": all_data}, f, indent=4)
    with open("example/taxonomy.owl", "w") as f:
        f.write(g_onto.serialize(format="xml"))
