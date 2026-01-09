"""Module builders for creating modules with a simplified API.

This module provides builders that hide the complexity of domain model construction,
allowing users to create modules with simple parameters instead of nested dataclasses.

DDD Layer: Application Layer
- Domain Layer: Complex domain models (FairModule, FairOptions, etc.)
- Application Layer: Simplified builders (this module)
- Users interact with application layer, not domain layer directly
"""

from typing import Optional, Dict, Any
from pathlib import Path

from facts_experiment_builder.core.modules.fair.module import (
    FairModule,
    FairInputs,
    FairOptions,
    FairInputPaths,
    FairOutputPaths,
)
from facts_experiment_builder.core.modules.bamber19_icesheets.module import (
    Bamber19IcesheetsModule,
    Bamber19Inputs,
    Bamber19Options,
    Bamber19IcesheetsInputPaths,
    Bamber19IcesheetsOutputPaths,
)
from facts_experiment_builder.core.modules.abcs.abcs import ScenarioConfig
from facts_experiment_builder.core.experiment.experiment import GlobalConfigOptions


class FairModuleBuilder:
    """Builder for creating FairModule with a simplified API."""
    
    def __init__(
        self,
        global_config: GlobalConfigOptions,
        input_dir: str,
        output_dir: str,
        rcmip_fname: str,
        param_fname: str,
        cyear_start: int,
        cyear_end: int,
        smooth_win: int,
        image: str,
        ohc_output: Optional[str] = None,
        gsat_output: Optional[str] = None,
        climate_output: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        """
        Initialize FairModule builder.
        
        Args:
            global_config: Global configuration options (pipeline_id, scenario, etc.)
            input_dir: Directory containing input files
            output_dir: Directory for output files
            rcmip_fname: Name of RCMIP emissions file
            param_fname: Name of parameters file
            cyear_start: Start year for calibration
            cyear_end: End year for calibration
            smooth_win: Smoothing window size
            image: Docker container image
            ohc_output: Output filename for OHC (defaults to "ohc.nc")
            gsat_output: Output filename for GSAT (defaults to "gsat.nc")
            climate_output: Output filename for climate (defaults to "climate.nc")
            seed: Random seed (defaults to global_config seed if available)
        """
        self.global_config = global_config
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.rcmip_fname = rcmip_fname
        self.param_fname = param_fname
        self.cyear_start = cyear_start
        self.cyear_end = cyear_end
        self.smooth_win = smooth_win
        self.image = image
        self.ohc_output = ohc_output or "ohc.nc"
        self.gsat_output = gsat_output or "gsat.nc"
        self.climate_output = climate_output or "climate.nc"
        self.seed = seed if seed is not None else getattr(global_config, 'seed', 1234)
    
    def build(self) -> FairModule:
        """
        Build and return a FairModule instance.
        
        Returns:
            Fully constructed FairModule
        """
        # Create scenario config
        scenario = ScenarioConfig(
            scenario_name=self.global_config.scenario,
            description=f"Scenario for {self.global_config.scenario}",
        )
        
        # Create FairOptions (hides TempModuleOptions complexity)
        fair_options = FairOptions(
            module_name="fair",
            scenario=scenario,
            pipeline_id=self.global_config.pipeline_id,
            nsamps=self.global_config.nsamps,
            seed=self.seed,
            cyear_start=self.cyear_start,
            cyear_end=self.cyear_end,
            smooth_win=self.smooth_win,
        )
        
        # Create paths (hides ModulePathsABC complexity)
        input_paths = FairInputPaths(
            fair_in_dir=self.input_dir,
            rcmip_fname=self.rcmip_fname,
            param_fname=self.param_fname,
        )
        
        output_paths = FairOutputPaths(
            fair_out_dir=self.output_dir,
            ohc_output=self.ohc_output,
            gsat_output=self.gsat_output,
            climate_output=self.climate_output,
        )
        
        # Create inputs (hides composition complexity)
        fair_inputs = FairInputs(
            fair_options=fair_options,
            input_paths=input_paths,
            output_paths=output_paths,
            image=self.image,
        )
        
        # Create and return module
        return FairModule(module_inputs=fair_inputs)


class Bamber19ModuleBuilder:
    """Builder for creating Bamber19IcesheetsModule with a simplified API."""
    
    def __init__(
        self,
        global_config: GlobalConfigOptions,
        input_dir: str,
        output_dir: str,
        slr_proj_mat_file: str,
        climate_data_file: str,
        replace: bool,
        image: str,
        ais_output: Optional[str] = None,
        eais_output: Optional[str] = None,
        wais_output: Optional[str] = None,
        gis_output: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        """
        Initialize Bamber19 module builder.
        
        Args:
            global_config: Global configuration options
            input_dir: Directory containing input files
            output_dir: Directory for output files
            slr_proj_mat_file: SLR projection matrix filename
            climate_data_file: Climate data filename
            replace: Whether to replace existing outputs
            image: Docker container image
            ais_output: AIS output filename (defaults to "ais_gslr.nc")
            eais_output: EAIS output filename (defaults to "eais_gslr.nc")
            wais_output: WAIS output filename (defaults to "wais_gslr.nc")
            gis_output: GIS output filename (defaults to "gis_gslr.nc")
            seed: Random seed (defaults to global_config seed if available)
        """
        self.global_config = global_config
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.slr_proj_mat_file = slr_proj_mat_file
        self.climate_data_file = climate_data_file
        self.replace = replace
        self.image = image
        self.ais_output = ais_output or "ais_gslr.nc"
        self.eais_output = eais_output or "eais_gslr.nc"
        self.wais_output = wais_output or "wais_gslr.nc"
        self.gis_output = gis_output or "gis_gslr.nc"
        self.seed = seed if seed is not None else getattr(global_config, 'seed', 1234)
    
    def build(self) -> Bamber19IcesheetsModule:
        """
        Build and return a Bamber19IcesheetsModule instance.
        
        Returns:
            Fully constructed Bamber19IcesheetsModule
        """
        # Create scenario config
        scenario = ScenarioConfig(
            scenario_name=self.global_config.scenario,
            description=f"Scenario for {self.global_config.scenario}",
        )
        
        # Create Bamber19Options (hides SealevelModuleOptions complexity)
        bamber_options = Bamber19Options(
            module_name="bamber19-icesheets",
            scenario=scenario,
            pipeline_id=self.global_config.pipeline_id,
            nsamps=self.global_config.nsamps,
            seed=self.seed,
            pyear_start=self.global_config.pyear_start,
            pyear_end=self.global_config.pyear_end,
            pyear_step=self.global_config.pyear_step,
            baseyear=self.global_config.baseyear,
            replace=self.replace,
        )
        
        # Create paths
        input_paths = Bamber19IcesheetsInputPaths(
            bamber19_icesheets_in_dir=self.input_dir,
            bamber19_slr_proj_mat_file=self.slr_proj_mat_file,
            climate_data_file=self.climate_data_file,
        )
        
        output_paths = Bamber19IcesheetsOutputPaths(
            bamber19_icesheets_out_dir=self.output_dir,
            bamber_ais_gslr_fname=self.ais_output,
            bamber_eais_gslr_fname=self.eais_output,
            bamber_wais_gslr_fname=self.wais_output,
            bamber_gis_gslr_fname=self.gis_output,
        )
        
        # Create inputs
        bamber_inputs = Bamber19Inputs(
            bamber_options=bamber_options,
            input_paths=input_paths,
            output_paths=output_paths,
            image=self.image,
        )
        
        # Create and return module
        return Bamber19IcesheetsModule(module_inputs=bamber_inputs)

