from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Literal, Optional

from pathlib import Path

InputPaths = TypeVar("InputPaths")
OutputPaths = TypeVar("OutputPaths")
ModuleSpecOptions = TypeVar("ModuleSpecOptions")
#ModuleContainerImage = TypeVar("ModuleContainerImage")

@dataclass(frozen=True)
class ModuleContainerImage:
    """Dataclass holding the container image for a module."""
    image_url: str
    image_tag: str

@dataclass(frozen=True)
class ScenarioConfig:
    """Dataclass holding scenario configuration details."""
    scenario_name: str
    description: str

@dataclass(frozen=True)
class ModuleOptions:
    """Dataclass holding the core options required of all modules (and required to be the same across all modules included in an experiment). 
    The part about being the same won't always be the case so need to think about overrides/how to handle that in those instances."""
    module_name: str
    scenario: ScenarioConfig
    pipeline_id: str
    nsamps: int
    seed: int
    pyear_start: Optional[int] = None
    pyear_end: Optional[int] = None
    pyear_step: Optional[int] = None
    baseyear: Optional[int] = None

class ModulePathsABC(ABC):
    """Abstract base class for module input and output paths. Checks that all required input paths exist and raises warning if output paths already exist."""
    def __init__(self,
                 path_type: Literal["input", "output"]
    ):
        self.path_type = path_type
        if self.path_type == "input":
            self.check_input_paths()
        elif self.path_type == "output":
            self.check_output_paths()
        
    @abstractmethod
    def get_path_mappings(self):
        """Returns a list of tuples mapping path names to Path objects."""
        pass

    def check_input_paths(self):
        """Check that all input paths exist."""
        path_mappings = self.get_path_mappings()
        for path_name, path in path_mappings:
            if not path.exists():
                raise FileNotFoundError(f"Input path {path_name} does not exist at {path}") 
    def check_output_paths(self):
        """Warn if files already exist at any specified output paths."""
        path_mappings = self.get_path_mappings()
        for path_name, path in path_mappings:
            if path.exists():
                print(f"Warning: Output path {path_name} already exists at {path}") 
   
