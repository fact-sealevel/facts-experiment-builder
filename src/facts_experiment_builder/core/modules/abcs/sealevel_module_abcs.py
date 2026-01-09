from facts_experiment_builder.core.modules.abcs.abcs import (
    ModulePathsABC, ModuleContainerImage, ScenarioConfig
)

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class SealevelModuleOptions:
    """Dataclass to hold options to be used in all instances of a sealevel module.
    This is JUST those options that are common across all sealevel modules. 
    Options specific to a given module will be in their own dataclass that inherits 
    from this one. """
    module_name: str 
    scenario: ScenarioConfig
    pipeline_id: str
    nsamps: int
    seed: int
    pyear_start: int
    pyear_end: int
    pyear_step: int
    baseyear: int

@dataclass(frozen=True)
class SealevelModuleInputs:
    """Dataclass to hold all inputs required for a subclass of the sealevel module ABC"""    
    sealevel_module_options: SealevelModuleOptions
    input_paths: ModulePathsABC
    output_paths: ModulePathsABC
    image: ModuleContainerImage

class HasSealevelModuleOptions(Protocol):
    """Protocol for objects that expose sealevel_module_options 
    (for compat. w/ module-specific stand-alone equivalents of SealevelModuleInputs)"""
    sealevel_module_options: SealevelModuleOptions

class SealevelModuleABC(ABC):    
    """ABC for all sealevel modules."""  
    def __init__(self,
                 module_inputs: SealevelModuleInputs
          ):
        self.module_inputs = module_inputs
    @property
    def module_name(self) -> str:
        return self.module_inputs.sealevel_module_options.module_name
    @property
    def pyear_start(self) -> int:
        return self.module_inputs.sealevel_module_options.pyear_start
    @property
    def pyear_end(self) -> int:
        return self.module_inputs.sealevel_module_options.pyear_end
    @property
    def pyear_step(self) -> int:
        return self.module_inputs.sealevel_module_options.pyear_step
    @property
    def baseyear(self) -> int:
        return self.module_inputs.sealevel_module_options.baseyear
    @property
    def scenario(self) -> ScenarioConfig:
        return self.module_inputs.sealevel_module_options.scenario
    @property
    def nsamps(self) -> int:
        return self.module_inputs.sealevel_module_options.nsamps
    @property
    def seed(self) -> int:  
        return self.module_inputs.sealevel_module_options.seed
    @property
    def pipeline_id(self) -> str:   
        return self.module_inputs.sealevel_module_options.pipeline_id
    @property
    def input_paths(self) -> ModulePathsABC:
        return self.module_inputs.input_paths
    @property
    def spec_options(self) -> SealevelModuleOptions: #TODO may want to make these unpack the module-spec options ?
        return self.module_inputs.sealevel_module_options
    @property
    def output_paths(self) -> ModulePathsABC:
        return self.module_inputs.output_paths
    @property
    def image(self) -> ModuleContainerImage:
        return self.module_inputs.image

    def get_compatibility_attrs(self) -> dict:

        opts = self.module_inputs.sealevel_module_options
        return {
            "module_name": opts.module_name,
            "scenario": opts.scenario,
            "pipeline_id": opts.pipeline_id,
            "nsamps": opts.nsamps,
            "seed": opts.seed,
            "pyear_start": opts.pyear_start,
            "pyear_end": opts.pyear_end,
            "pyear_step": opts.pyear_step,
            "baseyear": opts.baseyear,
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