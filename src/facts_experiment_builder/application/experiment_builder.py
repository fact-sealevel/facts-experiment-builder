"""Programmatic API for building experiments."""
from facts_experiment_builder.core.modules.fair.module import FairModule
from facts_experiment_builder.core.modules.bamber19_icesheets.module import Bamber19IcesheetsModule
from facts_experiment_builder.core.modules.abcs.abcs import ModuleOptions, ScenarioConfig

from pathlib import Path
from abc import ABC, abstractmethod

class Experiment(ABC):
    """ A FACTS 2 experiment"""
    
    def __init__(self, 
                experiment_name: str,
                pipeline_id: str,
                scenario: ScenarioConfig,
                baseyear: int,
                pyear_start: int,
                pyear_end: int,
                pyear_step: int,
                nsamps: int,
                seed: int,
                common_inputs_path: Path,
                location: ,
                v2_output_path: Path):
        self.experiment_name = experiment_name
        self.pipeline_id = pipeline_id
        self.scenario = scenario
        self.baseyear = baseyear
        self.pyear_start = pyear_start
        self.pyear_end = pyear_end
        self.pyear_step = pyear_step
        self.nsamps = nsamps
        self.seed = seed
        self.module_options = module_options

    def with_fair_module(self, **kwargs):
        """Add a fair module to the experiment."""
        self.temperature_module = FairModule(**kwargs)
        return self
    
    def with_fair2_module(self, **kwargs):
        raise NotImplementedError("Fair2 module is not implemented yet.")
    
    def build_experiment(self):
        """Build the experiment."""
        pass