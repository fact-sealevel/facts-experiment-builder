"""Protocols (ports) describing the interfaces the application expects to interact with
storage."""

from pathlib import Path
from typing import Protocol

from facts_experiment_builder.core.experiment.experiment import FactsExperiment
from facts_experiment_builder.core.module.module_schema import ModuleSchema


class ModuleRegistry(Protocol):
    """Protocol to access module registry data from storage."""

    def get_schema(self, module_name: str) -> ModuleSchema: ...
    def module_names(self) -> frozenset[str]: ...
    def version(self) -> str: ...


class ExperimentRepository(Protocol):
    """Protocol to add/get facts experiments from storage."""

    def add(
        self,
        experiment: FactsExperiment,
        config_path: Path,
        module_registry_version=None,
    ) -> None: ...
    def get(self, config_path: Path) -> dict: ...
