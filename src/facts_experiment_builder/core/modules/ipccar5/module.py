"""IPCC AR5 glaciers module implementation."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from facts_experiment_builder.core.modules.abcs.abcs import (
    ModuleContainerImage,
    ModulePathsABC,
)
from facts_experiment_builder.core.modules.abcs.sealevel_module_abcs import (
    SealevelModuleABC,
    SealevelModuleOptions
)

@dataclass(frozen=True)
class IPCCAR5GlaciersInputPaths(ModulePathsABC):
    """Input paths required for the IPCC AR5 glaciers module. Should follow the pattern:
    ipccar5_glaciers_in_dir/
    ipccar5_glaciers_param_fname
    """
    ipccar5_glaciers_in_dir: str
    ipccar5_glaciers_fraction_file: str

    def __post_init__(self):
        super().__init__(
            path_type="input"
        )
    def get_path_mappings(self) -> List[Tuple[str, Path]]:
        return [
            ("glacier_fraction_file", Path(self.ipccar5_glaciers_in_dir) / self.ipccar5_glaciers_fraction_file),
        ]

@dataclass(frozen=True)
class IPCCAR5GlaciersOutputPaths(ModulePathsABC):
    """Output paths required for the IPCC AR5 glaciers module. Should follow the pattern:
    ipccar5_glaciers_out_dir/
    ipccar5_glaciers_gslr_output_file
    """
    ipccar5_glaciers_out_dir: str
    ipccar5_glaciers_gslr_output_file: str
    def __post_init__(self):
        super().__init__(
            path_type="output"
        )
    def get_path_mappings(self) -> List[Tuple[str, Path]]:
        return [
            ("ipccar5_glaciers_gslr_output", Path(self.ipccar5_glaciers_out_dir) / self.ipccar5_glaciers_gslr_output_file),
        ]
        
@dataclass(frozen=True)
class IPCCAR5GlaciersOptions(SealevelModuleOptions):
    """IPCCAR5 glaciers-specific options (includes all sealevel module options + IPCCAR5 glaciers-specific).
    
    Inherits from SealevelModuleOptions:
    - module_name, scenario, pipeline_id, nsamps, seed
    - pyear_start, pyear_end, pyear_step, baseyear
    
    Adds IPCCAR5 glaciers-specific:
    - gmip: int
    - nmsamps: int (optional)
    - ntsamps: int (optional)
    """
    gmip: int
    nmsamps: int = None
    ntsamps: int = None

@dataclass(frozen=True)
class IPCCAR5GlaciersInputs:
    """A dataclass to hold all inputs required for the IPCC AR5 glaciers module."""
    options: IPCCAR5GlaciersOptions
    input_paths: IPCCAR5GlaciersInputPaths
    output_paths: IPCCAR5GlaciersOutputPaths
    image: ModuleContainerImage

    @property
    def sealevel_module_options(self) -> SealevelModuleOptions:
        return self.options

class IPCCAR5GlaciersModule(SealevelModuleABC):
    """An implementation of the IPCC AR5 glaciers module as a subclass of sealevel module ABC."""
    def __init__(self, module_inputs: IPCCAR5GlaciersInputs):
        super().__init__(module_inputs)

    def generate_compose_service(self):
        """Build a docker compose service to run the IPCC AR5 glaciers module."""
        compose_dict = {
            'image': self.image,
            'depends_on':
                {'fair_service':
                 {
                'condition', 'service_completed_successfully',
                    }
                },
            'volumes': {
                'ipccar5_glaciers_in_volume': self.input_paths.ipccar5_glaciers_in_dir,
                'ipccar5_glaciers_out_volume': self.output_paths.ipccar5_glaciers_out_dir,
                'fair_out_volume': 'fixme', #TODO ADD / FIGURE OUT 
            },
            'restart': 'no',
            'command': [
                "--pipeline-id", self.module_inputs.pipeline_id,
                "--scenario", self.module_inputs.scenario,
                "--climate-fname", self.input_paths.climate_fname,
                "--glacier-fraction-file", self.input_paths.glacier_fraction_file,
                "--start-year", self.module_inputs.start_year,
                "--pyear-start", self.module_inputs.pyear_start,
                "--pyear-end", self.module_inputs.pyear_end,
                "--pyear-step", self.module_inputs.pyear_step,
                "--nsamps", self.module_inputs.nsamps,
                "--seed", self.module_inputs.seed,
                "--gmip", self.module_inputs.gmip,
                "--nmsamps", self.module_inputs.nmsamps,
                "--ntsamps", self.module_inputs.ntsamps,
                "--global-output-file", self.output_paths.ipccar5_glaciers_gslr_output_file,
                "--local-output-file", self.output_paths.ipccar5_glaciers_lslr_output_file,
            ],
            }
        return compose_dict
    
    def generate_asyncflow_config(self):
        raise NotImplementedError("Asyncflow config generation not implemented for IPCC AR5 glaciers module.")
        
        