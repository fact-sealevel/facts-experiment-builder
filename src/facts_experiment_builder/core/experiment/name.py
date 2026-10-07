import re
from dataclasses import dataclass
from pathlib import Path

# Any character outside the allowed set: letters, digits, '.', '_' and '-'.
_INVALID_CHAR = re.compile(r"[^A-Za-z0-9._-]")


class InvalidExperimentNameError(Exception):
    def __init__(
        self,
        raw_name: str,
        reason: str | None = None,
    ):
        self.raw_name = raw_name
        self.reason = reason

        super().__init__(
            f"Received invalid experiment name '{self.raw_name}'."
            + (f" {self.reason}" if self.reason else "")
        )


def _invalid_part_reason(part: str) -> str | None:
    """Return why `part` is not an allowed path component, or None if it is valid."""
    if part == "":
        return "Experiment or directory name is empty."
    if part in (".", ".."):
        return f"{part!r} is not allowed as an experiment or directory name."
    bad = sorted(set(_INVALID_CHAR.findall(part)))
    if bad:
        chars = ", ".join(repr(c) for c in bad)
        return (
            f"{part!r} contains invalid character(s): {chars}. "
            "Only letters, digits, '.', '_' and '-' are allowed."
        )
    return None


@dataclass(frozen=True)
class ExperimentName:
    parent: Path | None
    name: str

    def __post_init__(self) -> None:
        reason = _invalid_part_reason(self.name)
        if reason:
            raise InvalidExperimentNameError(self.name, reason)
        if self.parent is not None:
            if self.parent.is_absolute():
                raise InvalidExperimentNameError(
                    str(self.parent), "Parent directory must be a relative path."
                )
            if not self.parent.parts:
                raise InvalidExperimentNameError(
                    str(self.parent), "Parent directory is empty."
                )
            for part in self.parent.parts:
                reason = _invalid_part_reason(part)
                if reason:
                    raise InvalidExperimentNameError(str(self.parent), reason)

    @classmethod
    def parse(cls, raw_name: str) -> "ExperimentName":
        p = Path(raw_name.strip())
        parent = p.parent if p.parent != Path(".") else None
        try:
            return cls(parent, p.name)
        except InvalidExperimentNameError as e:
            # Report the name as the user typed it, keeping the specific reason.
            raise InvalidExperimentNameError(raw_name, e.reason) from None

    @property
    def relative_path(self) -> Path:
        return self.parent / self.name if self.parent else Path(self.name)

    def __str__(self) -> str:
        return str(self.relative_path)
