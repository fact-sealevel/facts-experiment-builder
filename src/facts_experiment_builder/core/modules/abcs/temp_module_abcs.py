from facts_experiment_builder.core.modules.abcs.abcs import ModulePathsABC, ModuleContainerImage, ScenarioConfig

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union, Protocol 

@dataclass(frozen=True)
class TempModuleOptions:
    """Dataclass to hold options to be used in all instances of a temperature module."""
    module_name: str 
    scenario: ScenarioConfig
    pipeline_id: str
    nsamps: int
    seed: int
    # NOTE this is base class for all temp modules. subclasses hold module-specific options 
    # if some of these are not present in all temp modules, move to sublcasses.
   
@dataclass(frozen=True)    
class TempModuleInputs:
    """dataclass to hold all inputs required for a subclass of the temp module ABC"""
    temp_module_options: TempModuleOptions
    input_paths: ModulePathsABC
    output_paths: ModulePathsABC
    image: ModuleContainerImage

class HasTempModuleOptions(Protocol):
    """Protocol for objects that expose temp_module_options 
    (for compat. w/ module-specific stand-alone equivalents of TempModuleInputs)"""
    temp_module_options: TempModuleOptions

class TempModuleABC(ABC):
    """ABC for all temperature modules.
    NOTE: will need to change this if future temp modules (fair2?) have different options/params."""
    def __init__(self,
                 module_inputs: HasTempModuleOptions
          ):
        self.module_inputs = module_inputs

    @property
    def module_name(self) -> str:
        return self.module_inputs.temp_module_options.module_name
    @property
    def scenario(self) -> ScenarioConfig:
        return self.module_inputs.temp_module_options.scenario
    @property
    def nsamps(self) -> int:
        return self.module_inputs.temp_module_options.nsamps
    @property
    def seed(self) -> int:  
        return self.module_inputs.temp_module_options.seed
    @property
    def pipeline_id(self) -> str:
        return self.module_inputs.temp_module_options.pipeline_id
    @property
    def input_paths(self) -> ModulePathsABC:
        return self.module_inputs.input_paths
    @property
    def output_paths(self) -> ModulePathsABC:
        return self.module_inputs.output_paths
    @property
    def image(self) -> ModuleContainerImage:
        return self.module_inputs.image

    def get_compatibility_attrs(self) -> dict:

        opts = self.module_inputs.temp_module_options
        return {
            "module_name": opts.module_name,
            "scenario": opts.scenario,
            "cyear_start": opts.cyear_start,
            "cyear_end": opts.cyear_end,
            "nsamps": opts.nsamps,
            "seed": opts.seed,
        }
    
    @abstractmethod
    def check_attrs(self):
        pass
    @abstractmethod
    def generate_compose_service(self):
        pass
    @abstractmethod
    def generate_asyncflow_config(self):
        pass