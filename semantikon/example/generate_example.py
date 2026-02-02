from rdflib import RDF, Graph, OWL, Namespace
from typing import Annotated
from semantikon import ontology as onto
from semantikon.metadata import SemantikonURI, meta

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


uri_color = SemantikonURI(EX.Color)
uri_cleaned = SemantikonURI(EX.Cleaned)


class Clothes:
    pass


def wash(
    clothes: Clothes,
) -> Annotated[
    Clothes,
    {"triples": (EX.hasProperty, uri_cleaned), "derived_from": "inputs.clothes"},
]:
    ...
    return clothes


def dye(
    clothes: Clothes, color="blue"
) -> Annotated[
    Clothes, {"triples": (EX.hasProperty, uri_color), "derived_from": "inputs.clothes"}
]:
    ...
    return clothes


def sell(
    clothes: Annotated[
        Clothes,
        {
            "restrictions": (
                ((OWL.onProperty, EX.hasProperty), (OWL.someValuesFrom, EX.Cleaned)),
                ((OWL.onProperty, EX.hasProperty), (OWL.someValuesFrom, EX.Color)),
            )
        },
    ],
) -> int:
    ...
    return 10


g = onto.function_to_knowledge_graph(get_speed)
g += onto.function_to_knowledge_graph(get_kinetic_energy)
g += onto.function_to_knowledge_graph(wash)
g += onto.function_to_knowledge_graph(dye)
g += onto.function_to_knowledge_graph(sell)

with open("example_function_ontology.ttl", "w") as f:
    f.write(g.serialize(format="turtle"))
