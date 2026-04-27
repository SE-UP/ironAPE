from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List

class Config(BaseModel):
    ontology_path: str
    ontologyPrefixIRI: str
    tool_annotations_path: str
    constraints_path: str
    solutions_dir_path: str
    inputs: List[Dict[str, List[str]]]
    outputs: List[Dict[str, List[str]]]
    toolsTaxonomyRoot: str = Field(default="Tool")
    dataDimensionsTaxonomyRoots: List[str] = Field(default=["Type", "Format"])
    strict_tool_annotations: bool = False
    timeout_sec: float = 300
    solution_length: Dict[str, int] = Field(default={"min": 1, "max": 10})
    solutions: int = 1000
    number_of_execution_scripts: int = 3
    number_of_generated_graphs: int = 30
    number_of_cwl_files: int = 5
    tool_seq_repeat: bool = False
    debug_mode: bool = True
    use_workflow_input: str = "all"
    use_all_generated_data: str = "one"

    model_config = ConfigDict(strict=True)  # Enforce strict type checking

