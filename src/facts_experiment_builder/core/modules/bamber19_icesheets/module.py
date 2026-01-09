"""Bamber19 Icesheets module implementation."""

import yaml
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

# Load defaults from YAML file
_DEFAULTS_PATH = Path(__file__).parent / "defaults.yml"
_BAMBER_DEFAULTS = {}
if _DEFAULTS_PATH.exists():
    with open(_DEFAULTS_PATH, 'r') as f:
        _BAMBER_DEFAULTS = yaml.safe_load(f) or {}
else:
    # Fallback defaults if YAML doesn't exist
    _BAMBER_DEFAULTS = {
        "options": {"replace": True},
        "inputs": {
            "bamber19_slr_proj_mat_file": "SLRProjections190726core_SEJ_full.mat",
        },
        "image": {
            "image_url": "ghcr.io/fact-sealevel/bamber19-icesheets:0.1.0",
            "image_tag": "0.1.0",
        },
    }

@dataclass(frozen=True)
class Bamber19IcesheetsContainerImage(ModuleContainerImage):
    """Dataclass holding the container image for the Bamber19 Icesheets module."""
    image_url: str = _BAMBER_DEFAULTS.get("image", {}).get("image_url", "ghcr.io/fact-sealevel/bamber19-icesheets:0.1.0")
    image_tag: str = _BAMBER_DEFAULTS.get("image", {}).get("image_tag", "0.1.0")

@dataclass
class Bamber19IcesheetsInputPaths(ModulePathsABC):
    """Input paths required for the Bamber19 Icesheets module. Should follow the pattern:
    bamber19_icesheets_in_dir/
    bamber19_icesheets_param_fname
    """
    bamber19_icesheets_in_dir: str
    climate_data_file: str
    bamber19_slr_proj_mat_file: str = _BAMBER_DEFAULTS.get("inputs", {}).get("bamber19_slr_proj_mat_file", "SLRProjections190726core_SEJ_full.mat")

    def __post_init__(self):
        super().__init__(
            path_type="input"
        )
    def get_path_mappings(self) -> List[Tuple[str, Path]]:
        """Return path mappings for validation.
        
        Note: climate_data_file is not validated here because it comes from
        fair output (mounted as a volume), not from bamber19 input directory.
        """
        return [
            ("slr_projection_matrix_file", Path(self.bamber19_icesheets_in_dir) / self.bamber19_slr_proj_mat_file),
            # climate_data_file is excluded from validation because it comes from fair output,
            # not from bamber19 input directory. It will be mounted as a volume at runtime.
        ]
    
@dataclass
class Bamber19IcesheetsOutputPaths(ModulePathsABC):
    """Paths for outputs written by the Bamber19 Icesheets module. Should follow the pattern:
     bamber19_icesheets_out_dir/
    """
    bamber19_icesheets_out_dir: str
    bamber_ais_gslr_fname: str
    bamber_eais_gslr_fname: str
    bamber_wais_gslr_fname: str
    bamber_gis_gslr_fname: str
    
    def __post_init__(self):
        super().__init__(
            path_type="output"
        )
    def get_path_mappings(self) -> List[Tuple[str, Path]]:
        return [
            ("bamber_ais_gslr_output", Path(self.bamber19_icesheets_out_dir) / self.bamber_ais_gslr_fname),
            ("bamber_eais_gslr_output", Path(self.bamber19_icesheets_out_dir) / self.bamber_eais_gslr_fname),
            ("bamber_wais_gslr_output", Path(self.bamber19_icesheets_out_dir) / self.bamber_wais_gslr_fname),
            ("bamber_gis_gslr_output", Path(self.bamber19_icesheets_out_dir) / self.bamber_gis_gslr_fname),
        ]


@dataclass(frozen=True)
class Bamber19Options(SealevelModuleOptions):
    """Bamber19-specific options (includes all sealevel options + Bamber19-specific).
    
    Inherits from SealevelModuleOptions:
    - module_name, scenario, pipeline_id, nsamps, seed
    - pyear_start, pyear_end, pyear_step, baseyear
    
    Adds Bamber19-specific:
    - replace: bool
    """
    replace: bool = _BAMBER_DEFAULTS.get("options", {}).get("replace", True)

@dataclass(frozen=True)
class Bamber19Inputs:
    """A dataclass to hold all inputs required for the Bamber19 Icesheets module."""  
    bamber_options: Bamber19Options
    input_paths: Bamber19IcesheetsInputPaths
    output_paths: Bamber19IcesheetsOutputPaths
    image: Bamber19IcesheetsContainerImage

    @property
    def sealevel_module_options(self) -> SealevelModuleOptions:
        return self.bamber_options 

class Bamber19IcesheetsModule(SealevelModuleABC):
    """An implementation of the bamber19 icesheets module as a subclass of sealevel module ABC.""" 
    def __init__(self, module_inputs: Bamber19Inputs):
        super().__init__(module_inputs)

    def check_attrs(self):
        """Check that required attributes are present."""
        pass

    def generate_compose_service(self, fair_output_dir: str = None):
        """Build a docker compose service to run the Bamber19 Icesheets module.
        
        Args:
            fair_output_dir: Path to fair output directory (for mounting fair outputs)
        
        Returns a service configuration with:
        - image: container image
        - depends_on: dependency on fair service
        - volumes: host:container mappings including fair output
        - command: CLI arguments using container paths
        - restart: 'no'
        """
        # Extract filenames from output paths
        ais_filename = Path(self.output_paths.bamber_ais_gslr_fname).name
        eais_filename = Path(self.output_paths.bamber_eais_gslr_fname).name
        wais_filename = Path(self.output_paths.bamber_wais_gslr_fname).name
        gis_filename = Path(self.output_paths.bamber_gis_gslr_fname).name
        
        volumes = [
            f"{self.input_paths.bamber19_icesheets_in_dir}:/mnt/bamber19_icesheets_in",
            f"{self.output_paths.bamber19_icesheets_out_dir}:/mnt/bamber19_icesheets_out",
        ]
        
        # Add fair output volume if provided
        if fair_output_dir:
            volumes.append(f"{fair_output_dir}:/mnt/fair_out")
        
        compose_dict = {
            'image': self.image,
            'depends_on': {
                'fair': {
                    'condition': 'service_completed_successfully'
                }
            },
            'volumes': volumes,
            'restart': 'no',
            'command': [
                f"--pipeline-id={self.pipeline_id}",
                f"--nsamps={self.nsamps}",
                f"--baseyear={self.baseyear}",
                f"--pyear-start={self.pyear_start}",
                f"--pyear-end={self.pyear_end}",
                f"--pyear-step={self.pyear_step}",
                f"--scenario={self.scenario.scenario_name}",
                f"--seed={self.seed}",
                f"--replace={self.module_inputs.bamber_options.replace}",
                f"--climate-data-file=/mnt/fair_out/{Path(self.input_paths.climate_data_file).name}" if fair_output_dir else f"--climate-data-file={self.input_paths.climate_data_file}",
                f"--slr-proj-mat-file=/mnt/bamber19_icesheets_in/{self.input_paths.bamber19_slr_proj_mat_file}",
                f"--ais-gslr-outfile=/mnt/bamber19_icesheets_out/{ais_filename}",
                f"--eais-gslr-outfile=/mnt/bamber19_icesheets_out/{eais_filename}",
                f"--wais-gslr-outfile=/mnt/bamber19_icesheets_out/{wais_filename}",
                f"--gis-gslr-outfile=/mnt/bamber19_icesheets_out/{gis_filename}",
            ],
        }
        return compose_dict
    def generate_asyncflow_config(self):
        raise NotImplementedError("Asyncflow config generation not yet implemented for Bamber19 Icesheets module.")

