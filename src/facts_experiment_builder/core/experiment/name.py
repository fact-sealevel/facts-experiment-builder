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


@dataclass(frozen=True)
class ExperimentName:
    parent: Path | None
    name: str

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
