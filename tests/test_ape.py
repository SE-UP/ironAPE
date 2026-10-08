import unittest
from pathlib import Path
from typing import Annotated

from rdflib import Namespace
from semantikon import ontology as onto
from semantikon.metadata import meta

from ironape.run import cwl_to_flowrep

EX = Namespace("http://pyiron.org/ontology/")


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


class TestAPE(unittest.TestCase):
    def test_full_run(self):
        g = onto.function_to_knowledge_graph(get_speed)
        g += onto.function_to_knowledge_graph(get_kinetic_energy)
        workflow_path = Path(__file__).resolve().parent / "static/kinetic_energy/candidate_workflow_1.cwl"
        print(cwl_to_flowrep(str(workflow_path), g))


if __name__ == "__main__":
    unittest.main()
