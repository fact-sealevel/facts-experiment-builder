from pathlib import Path
from typing import List
from facts_experiment_builder.core.experiment.facts_experiment import ExperimentState


class ExperimentRegistry:
    def __init__(self, registry_dir: Path):
        self._registry_dir = registry_dir

    @classmethod
    def default(cls) -> "ExperimentRegistry":
        from facts_experiment_builder.infra.path_manager import (
            get_experiment_registry_path,
        )

        return cls(get_experiment_registry_path())

    def list_experiments(self) -> List[str]:
        """Return names of all experiments in the registry."""
        return [d.name for d in self._registry_dir.iterdir() if d.is_dir()]
        # TODO would be ideal to be able to show state (initialized, completed, run) of each experiment
        # but this would require a different approach to the registry.

    def get_experiment_path(self, experiment_name: str) -> Path:
        """Return path to the experiment directory."""
        return self._registry_dir / experiment_name

    def get_experiment_metadata_path(self, experiment_name: str) -> Path:
        """Return path to the experiment metadata file."""
        # raise NotImplementedError("Not implemented")
        return self._registry_dir / experiment_name / "experiment-config.yaml"

    def get_experiment_compose_path(self, experiment_name: str) -> Path:
        """Return path to the experiment compose file."""
        return self._registry_dir / experiment_name / "experiment-compose.yaml"

    def get_experiment_state(self, experiment_name: str) -> ExperimentState:
        raise NotImplementedError("Not implemented")
