"""Protocol (port) for the execution backends that generate_run_file() writes for, e.g.
Docker Compose or an Apptainer bash script."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from facts_experiment_builder.application.execution_graph import ExecutionGraph
from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.io.paths import ExperimentPaths


@dataclass(frozen=True)
class RunInfo:
    """Experiment-level values a backend may need besides the services."""

    config: LoadedExperimentConfig
    data_paths: ExperimentDataPaths  # after ExecutionBackend.data_paths()
    workspace_dir: Path
    workflow_names: list[str]  # in experiment-config.yaml order


class ExecutionBackend(Protocol):
    """Protocol to turn an ExecutionGraph into a run file and write it."""

    def default_output_path(self, experiment_paths: ExperimentPaths) -> Path:
        """Where to write the run file when no custom path is given."""
        ...

    def data_paths(
        self, data_paths: ExperimentDataPaths, experiment_paths: ExperimentPaths
    ) -> ExperimentDataPaths:
        """Return the experiment paths this backend's services should use.

        Called before module specs are built, since they fix their paths then.
        """
        ...

    def render(self, graph: ExecutionGraph, info: RunInfo) -> str: ...

    def write(self, content: str, path: Path) -> None: ...
