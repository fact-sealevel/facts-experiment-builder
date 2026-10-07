from dataclasses import dataclass
from pathlib import Path

from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
    ExperimentOutsideWorkspaceError,
    ExperimentParentNotFoundError,
)
from facts_experiment_builder.core.experiment.name import ExperimentName

_CONFIG_FILENAME = "experiment-config.yaml"
_COMPOSE_FILENAME = "experiment-compose.yaml"
_APPTAINER_FILENAME = "experiment-apptainer.sh"
_OUTPUT_DIRNAME = "output"


@dataclass
class ExperimentPaths:
    """
    This is a class to hold all paths related to an experiment including:
    - Experiment directory
    - Experiment parent directory (if exists)
    - Experiment output directory
    - Experiment config file
    - Experiment compose file
    """

    workspace_dir: Path
    experiment_name: ExperimentName

    def __post_init__(self) -> None:
        if not self.workspace_dir.is_absolute():
            raise ValueError(f"'{self.workspace_dir}.is_absolute()' must be True")

    @property
    def experiment_dir(self) -> Path:
        return self.workspace_dir / self.experiment_name.relative_path

    @property
    def parent_dir(self) -> Path:
        return self.experiment_dir.parent

    @property
    def output_dir(self) -> Path:
        return self.experiment_dir / _OUTPUT_DIRNAME

    @property
    def config_path(self) -> Path:
        return self.experiment_dir / _CONFIG_FILENAME

    @property
    def compose_path(self) -> Path:
        return self.experiment_dir / _COMPOSE_FILENAME

    @property
    def apptainer_script_path(self) -> Path:
        return self.experiment_dir / _APPTAINER_FILENAME


def check_experiment_does_not_exist(experiment_paths: ExperimentPaths) -> None:
    """Raise if an experiment already exists, i.e. its experiment-config.yaml exists."""
    if experiment_paths.config_path.exists():
        raise ExperimentAlreadyExistsError(path=str(experiment_paths.experiment_dir))


def check_experiment_location(experiment_paths: ExperimentPaths) -> None:
    """Raise if the experiment directory would fall outside the workspace (e.g. via a
    symlinked parent) or if its parent directory does not exist.

    Parent directories are never created; they must already exist in the workspace.
    """
    workspace_dir = experiment_paths.workspace_dir.resolve()
    target = experiment_paths.experiment_dir.resolve()
    if not target.is_relative_to(workspace_dir):
        raise ExperimentOutsideWorkspaceError(
            experiment_paths.experiment_name, target, workspace_dir
        )
    if not experiment_paths.parent_dir.is_dir():
        raise ExperimentParentNotFoundError(
            experiment_paths.experiment_name, experiment_paths.workspace_dir
        )


def create_experiment_dir(experiment_paths: ExperimentPaths) -> None:
    """Create the experiment directory if needed.

    Its parent must already exist.
    """
    check_experiment_location(experiment_paths)
    try:
        experiment_paths.experiment_dir.mkdir(parents=False, exist_ok=True)
    except FileNotFoundError:
        # Parent removed since check_experiment_location()
        raise ExperimentParentNotFoundError(
            experiment_paths.experiment_name, experiment_paths.workspace_dir
        ) from None
