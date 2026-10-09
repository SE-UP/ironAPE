import unittest

from rdflib import Graph

from ironape.converter import knowledge_graph_to_ape


class TestKnowledgeGraphToApe(unittest.TestCase):
    def test_knowledge_graph_to_ape_empty_graph(self):
        graph = Graph()
        all_data, g_onto = knowledge_graph_to_ape(graph)
        assert all_data == []
        assert g_onto is not None


if __name__ == "__main__":
    unittest.main()
