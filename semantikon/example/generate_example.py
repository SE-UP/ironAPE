from rdflib import RDF, Graph, Namespace
from typing import Annotated
from semantikon import ontology as onto
from semantikon.metadata import meta


EX = Namespace("http://example.org/")


def get_speed(
    distance: Annotated[float, {"uri": EX.Distance}],
    time: Annotated[float, {"uri": EX.time}],
) -> Annotated[float, {"uri": EX.Velocity}]:
    """some random docstring"""
    speed = distance / time
    return speed


@meta(uri=EX.getKineticEnergy)
def get_kinetic_energy(
    mass: Annotated[float, {"uri": EX.Mass}],
    velocity: Annotated[float, {"uri": EX.Velocity}],
) -> Annotated[float, {"uri": EX.KineticEnergy}]:
    return 0.5 * mass * velocity**2


g = onto.function_to_knowledge_graph(get_speed)
g += onto.function_to_knowledge_graph(get_kinetic_energy)

with open("example_function_ontology.ttl", "w") as f:
    f.write(g.serialize(format="turtle"))
