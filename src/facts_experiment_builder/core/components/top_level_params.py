"""Experiment-wide top-level parameters (pipeline-id, scenario, years, nsamps, ...).

Lives in core/components (not core/experiment) so that core/module can depend on it
without importing upward into the experiment layer.
"""

from dataclasses import dataclass, fields
from typing import Any


@dataclass
class TopLevelParams:
    pipeline_id: str | None = None
    scenario: str | None = None
    baseyear: int | None = None
    pyear_start: int | None = None
    pyear_end: int | None = None
    pyear_step: int | None = None
    nsamps: int | None = None
    location_file: str | None = None

    @classmethod
    def from_config(cls, metadata: dict[str, Any]) -> "TopLevelParams":
        """Build from a loaded experiment-config.yaml dict.

        Config keys may be kebab-case ("pipeline-id") or snake_case ("pipeline_id"). A
        config only contains the top-level params its modules reference, so any param
        not present is left as None.
        """
        values = {}
        for f in fields(cls):
            kebab = f.name.replace("_", "-")
            if kebab in metadata:
                values[f.name] = metadata[kebab]
            elif f.name in metadata:
                values[f.name] = metadata[f.name]
        return cls(**values)


TOP_LEVEL_PARAM_NAMES: frozenset[str] = frozenset(
    f.name for f in fields(TopLevelParams)
)
