from dataclasses import dataclass
from pathlib import Path
import re

_VALID = re.compile(r"^[A-Za-z0-9._-]+$")


class InvalidExperimentNameError(Exception):
    def __init__(
        self,
        raw_name: str,
    ):
        self.raw_name = raw_name

        super().__init__(f"Received invalid experiment name '{self.raw_name}'.")


def _valid_segment(s: str) -> bool:
    return _VALID.fullmatch(s) is not None and s not in (".", "..")


@dataclass(frozen=True)
class ExperimentName:
    """A user-supplied experiment name, optionally includes a parent directory name.

    Invariant: `relative_path` is always a non-empty, relative, traversal-free path whose every segment matches `_VALID`.

    A valid `ExperimentName` doesn't imply existence of corresponding directory.
    """

    parent: Path | None
    name: str

    def __post_init__(self) -> None:
        if not _valid_segment(self.name):
            raise InvalidExperimentNameError(self.name)

        if not _VALID.fullmatch(self.name):
            raise InvalidExperimentNameError(self.name)
        if self.parent is not None:
            parts = self.parent.parts
            if self.parent.is_absolute() or not parts or ".." in parts:
                raise InvalidExperimentNameError(str(self.parent))
            if not all(_valid_segment(part) for part in parts):
                raise InvalidExperimentNameError(str(self.parent))

    @classmethod
    def parse(cls, raw_name: str) -> "ExperimentName":
        p = Path(raw_name.strip())
        parent = p.parent if p.parent != Path(".") else None
        name = p.name
        return cls(parent, name)

    @property
    def relative_path(self) -> Path:
        return self.parent / self.name if self.parent else Path(self.name)

    def __str__(self) -> str:
        return str(self.relative_path)
