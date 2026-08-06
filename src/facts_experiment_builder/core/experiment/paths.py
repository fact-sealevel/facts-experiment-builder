"""Module for logic around experiment paths, including experiment name."""

from pathlib import Path
import re
from dataclasses import dataclass

_VALID = re.compile(r"^[A-Za-z0-9._-]+$")


class InvalidExperimentNameError(Exception):
    def __init__(
        self,
        raw_name: str,
    ):
        self.raw_name = raw_name

        super().__init__(f"Received invalid experiment name '{self.raw_name}'.")


_CONFIG_FILENAME = "experiment-config.yaml"
_COMPOSE_FILENAME = "experiment-compose.yaml"
_OUTPUT_DIRNAME = "output"


@dataclass(frozen=True)
class ExperimentName:
    parent: Path | None
    name: str

    def __post_init__(self) -> None:
        if not _VALID.fullmatch(self.name):
            raise InvalidExperimentNameError(self.name)
        if self.parent is not None:
            parts = self.parent.parts
            if self.parent.is_absolute() or not parts or ".." in parts:
                raise InvalidExperimentNameError(str(self.parent))
            if not all(_VALID.fullmatch(part) for part in parts):
                raise InvalidExperimentNameError(str(self.parent))

    @classmethod
    def parse(cls, raw_name: str) -> "ExperimentName":
        p = Path(raw_name.strip())

        if not all(_VALID.match(part) and part not in (".", "..") for part in p.parts):
            raise InvalidExperimentNameError(raw_name)
        if not p.name or p.is_absolute() or ".." in p.parts:
            raise InvalidExperimentNameError(raw_name)
        parent = p.parent if p.parent != Path(".") else None
        name = p.name
        return cls(parent, name)

    @property
    def relative_path(self) -> Path:
        return self.parent / self.name if self.parent else Path(self.name)

    def __str__(self) -> str:
        return str(self.relative_path)


@dataclass
class ExperimentPathContainer:
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
