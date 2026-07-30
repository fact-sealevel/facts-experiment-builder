from pathlib import Path
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)

_CONFIG_FILENAME = "experiment-config.yaml"
_COMPOSE_FILENAME = "experiment-compose.yaml"
_OUTPUT_DIRNAME = "output"


class ExperimentStorageError(Exception):
    def __init__(self, experiment_name: ExperimentName, target: Path, root: Path):
        self.experiment_name = experiment_name
        super().__init__(f"Expected target '{target} to be relative to {root}.")


class ExperimentRootNotFoundError(Exception):
    def __init__(self, root: Path):
        self.root = root
        super().__init__(f"Root '{root} not found.")


class ExperimentParentNotFoundError(Exception):
    def __init__(self, experiment_name: ExperimentName, root: Path):
        self.experiment_name = experiment_name
        self.root = root
        super().__init__(
            f"Cannot create experiment '{experiment_name}': parent directory "
            f"'{experiment_name.parent}' does not exist under root '{root}'"
        )


class FileSystemExperimentStorage:
    def __init__(self, root: Path):
        if not root.is_absolute():
            raise ValueError("storage root must be absolute")
        if not root.is_dir():
            raise ExperimentRootNotFoundError(root)
        self._root = root

    def create(self, exp: ExperimentName) -> Path:
        """Creates directory for specified experiment name."""
        target = (self._root / exp.relative_path).resolve()
        if not target.is_relative_to(self._root):
            raise ExperimentStorageError(exp, target=target, root=self._root)
        try:
            target.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            raise ExperimentAlreadyExistsError(exp) from None
        except FileNotFoundError:
            raise ExperimentParentNotFoundError(exp, self._root) from None
        (target / _OUTPUT_DIRNAME).mkdir()
        return target

    def config_path(self, exp: ExperimentName) -> Path:
        return self._target_for(exp) / _CONFIG_FILENAME

    def compose_path(self, exp: ExperimentName) -> Path:
        return self._target_for(exp) / _COMPOSE_FILENAME

    def _target_for(self, exp: ExperimentName) -> Path:
        target = (self._root / exp.relative_path).resolve()
        if not target.is_relative_to(self._root):
            raise ExperimentStorageError(exp, target=target, root=self._root)
        return target

    def experiment_dir(self, exp: ExperimentName):
        """Returns the path to an experiment directory based on name and storage
        location."""
        return self._target_for(exp)
