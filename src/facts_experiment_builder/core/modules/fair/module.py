"""FAIR module implementation."""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from facts_experiment_builder.core.modules.abcs.abcs import (
    ModuleContainerImage,
    ModulePathsABC,
)
from facts_experiment_builder.core.modules.abcs.temp_module_abcs import (
    TempModuleABC,
    TempModuleOptions,
)

# Load defaults from YAML file
_DEFAULTS_PATH = Path(__file__).parent / "defaults.yml"
_FAIR_DEFAULTS = {}
if _DEFAULTS_PATH.exists():
    with open(_DEFAULTS_PATH, 'r') as f:
        _FAIR_DEFAULTS = yaml.safe_load(f) or {}
else:
    # Fallback defaults if YAML doesn't exist
    _FAIR_DEFAULTS = {
        "options": {"cyear_start": 1850, "cyear_end": 1900, "smooth_win": 19},
        "inputs": {
            "fair_in_dir": "$HOME/Desktop/facts_work/facts_v2/fair/data/input",
            "rcmip_fname": "rcmip",
            "param_fname": "parameters",
        },
        "image": {
            "image_url": "ghcr.io/fact-sealevel/fair-temperature:0.2.1",
            "image_tag": "0.2.1",
        },
    }

@dataclass(frozen=True)
class FairContainerImage(ModuleContainerImage):
    """Dataclass holding the container image for the FAIR module."""
    image_url: str = _FAIR_DEFAULTS.get("image", {}).get("image_url", "ghcr.io/fact-sealevel/fair-temperature:0.2.1")
    image_tag: str = _FAIR_DEFAULTS.get("image", {}).get("image_tag", "0.2.1")

@dataclass
class FairInputPaths(ModulePathsABC):
    """Input paths required for the FAIR module. Should follow the pattern:
    fair_in_dir/
    rcmip_fname
    param_fname
    """
    fair_in_dir: str = _FAIR_DEFAULTS.get("inputs", {}).get("fair_in_dir", "$HOME/Desktop/facts_work/facts_v2/fair/data/input")
    rcmip_fname: str = _FAIR_DEFAULTS.get("inputs", {}).get("rcmip_fname", "rcmip")
    param_fname: str = _FAIR_DEFAULTS.get("inputs", {}).get("param_fname", "parameters")

    def __post_init__(self):
        super().__init__(
            path_type="input"
        )

    def get_path_mappings(self) -> List[Tuple[str, Path]]:
        return [
            ("rcmip_file", Path(self.fair_in_dir) / self.rcmip_fname),
            ("param_file", Path(self.fair_in_dir) / self.param_fname),
        ]

@dataclass
class FairOutputPaths(ModulePathsABC):
    """Paths for outputs written by the FAIR module. Should follow the pattern:
     fair_out_dir/
     ohc_output_fname
     gsat_output_fname
     climate_output_fname
    """
    fair_out_dir: str
    ohc_output: str
    gsat_output: str
    climate_output: str

    def __post_init__(self):
        super().__init__(
            path_type="output"
        )

    def get_path_mappings(self) -> List[Tuple[str, Path]]:
        return [
            ("ohc_output", Path(self.fair_out_dir) / self.ohc_output),
            ("gsat_output", Path(self.fair_out_dir) / self.gsat_output),
            ("climate_output", Path(self.fair_out_dir) / self.climate_output),
        ]
    

@dataclass(frozen=True)
class FairOptions(TempModuleOptions):
    """FAIR-specific options (includes all temp module options).
    
    All fields are inherited from TempModuleOptions:
    - module_name, scenario, pipeline_id, nsamps, seed
    - cyear_start, cyear_end, smooth_win
    """
    cyear_start: int = _FAIR_DEFAULTS.get("options", {}).get("cyear_start", 1850)
    cyear_end: int = _FAIR_DEFAULTS.get("options", {}).get("cyear_end", 1900)
    smooth_win: int = _FAIR_DEFAULTS.get("options", {}).get("smooth_win", 19)

@dataclass(frozen=True)
class FairInputs:
    """A dataclass to hold all inputs required for a FAIR module."""
    fair_options: FairOptions
    input_paths: FairInputPaths
    output_paths: FairOutputPaths
    image: FairContainerImage

    @property
    def temp_module_options(self) -> TempModuleOptions:
        return self.fair_options
    
class FairModule(TempModuleABC):
    """An implementation of the FAIR sealevel module. It holds all necessary input data and options to run the fair module. It will hold methods that implement the module in different execution environments (e.g., docker-compose, asyncflow, etc.)."""
    def __init__(self, module_inputs: FairInputs):
        super().__init__(module_inputs)
        self.fair_options = module_inputs.fair_options

    @property
    def cyear_start(self) -> int:
        return self.fair_options.cyear_start
    @property
    def cyear_end(self) -> int:
        return self.fair_options.cyear_end
    @property
    def smooth_win(self) -> int:
        return self.fair_options.smooth_win

    def check_attrs(self):
        """Check that required attributes are present."""
        pass

    def generate_compose_service(self):
        """Build a docker-compose service to run the fair module.
        
        Returns a service configuration with:
        - image: container image
        - volumes: host:container mappings
        - command: CLI arguments using container paths
        - restart: 'no'
        """
        # Extract just the filename from output paths (they're relative to output dir)
        ohc_filename = Path(self.output_paths.ohc_output).name
        gsat_filename = Path(self.output_paths.gsat_output).name
        climate_filename = Path(self.output_paths.climate_output).name
        
        compose_dict = {
            'image': self.image,
            'volumes': [
                f"{self.input_paths.fair_in_dir}:/mnt/fair_in",
                f"{self.output_paths.fair_out_dir}:/mnt/fair_out",
            ],
            'restart': 'no',
            'command': [
                f"--pipeline-id={self.pipeline_id}",
                f"--nsamps={self.nsamps}",
                f"--scenario={self.scenario.scenario_name}",
                f"--seed={self.seed}",
                f"--cyear-start={self.cyear_start}",
                f"--cyear-end={self.cyear_end}",
                f"--smooth-win={self.smooth_win}",
                f"--rcmip-file=/mnt/fair_in/{self.input_paths.rcmip_fname}",
                f"--param-file=/mnt/fair_in/{self.input_paths.param_fname}",
                f"--output-ohc-file=/mnt/fair_out/{ohc_filename}",
                f"--output-gsat-file=/mnt/fair_out/{gsat_filename}",
                f"--output-climate-file=/mnt/fair_out/{climate_filename}",
            ]
        }
        return compose_dict
    
    def generate_asyncflow_config(self):
        raise NotImplementedError("Asyncflow config generation not implemented for FairModule.")

