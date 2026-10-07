import re
from dataclasses import dataclass
from pathlib import Path

_VALID = re.compile(r"^[A-Za-z0-9._-]+$")


class InvalidExperimentNameError(Exception):
    def __init__(
        self,
        raw_name: str,
    ):
        self.raw_name = raw_name

        super().__init__(f"Received invalid experiment name '{self.raw_name}'.")


def _is_valid_part(part: str) -> bool:
    """True if part is a single allowed path component (not '.' or '..')."""
    return bool(_VALID.fullmatch(part)) and part not in (".", "..")


@dataclass(frozen=True)
class ExperimentName:
    parent: Path | None
    name: str

    def __post_init__(self) -> None:
        if not _is_valid_part(self.name):
            raise InvalidExperimentNameError(self.name)
        if self.parent is not None:
            parts = self.parent.parts
            if (
                self.parent.is_absolute()
                or not parts
                or not all(_is_valid_part(part) for part in parts)
            ):
                raise InvalidExperimentNameError(str(self.parent))

    @classmethod
    def parse(cls, raw_name: str) -> "ExperimentName":
        p = Path(raw_name.strip())
        parent = p.parent if p.parent != Path(".") else None
        try:
            return cls(parent, p.name)
        except InvalidExperimentNameError:
            # Report the name as the user typed it, not the failing component.
            raise InvalidExperimentNameError(raw_name) from None

    @property
    def relative_path(self) -> Path:
        return self.parent / self.name if self.parent else Path(self.name)

    def __str__(self) -> str:
        return str(self.relative_path)
