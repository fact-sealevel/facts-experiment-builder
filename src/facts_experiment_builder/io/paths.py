from dataclasses import dataclass
from pathlib import Path

from facts_experiment_builder.core.experiment.name import ExperimentName

_CONFIG_FILENAME = "experiment-config.yaml"
_MODULE_SCHEMAS_FILENAME = "module-schemas.yaml"
_COMPOSE_FILENAME = "experiment-compose.yaml"
_OUTPUT_DIRNAME = "output"


@dataclass
class ExperimentPaths:
    """
    This is a class to hold all paths related to an experiment including:
    - Experiment directory
    - Experiment parent directory (if exists)
    - Experiment output directory
    - Experiment config file
    - Module schemas file
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
    def module_schemas_path(self) -> Path:
        return self.experiment_dir / _MODULE_SCHEMAS_FILENAME

    @property
    def compose_path(self) -> Path:
        return self.experiment_dir / _COMPOSE_FILENAME


def make_output_dir(experiment_paths: ExperimentPaths) -> None:
    output_dir = experiment_paths.output_dir
    output_dir.mkdir(parents=True)
