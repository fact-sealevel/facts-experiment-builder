"""Experiment-wide top-level parameters (pipeline-id, scenario, years, nsamps, ...).

Lives in core/components (not core/experiment) so that core/module can depend on it
without importing upward into the experiment layer.
"""

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from facts_experiment_builder.core.experiment.loaded_config import (
        LoadedExperimentConfig,
    )


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
    def from_loaded_config(cls, config: "LoadedExperimentConfig") -> "TopLevelParams":
        """Build from a LoadedExperimentConfig's typed fields.

        Equivalent to from_config() on the loaded mapping: every field here is one of
        the config's captured fields. location_file falls back to a snake_case
        'location_file' key in other_top_level_values, as from_config() allows.
        """
        return cls(
            pipeline_id=config.pipeline_id,
            scenario=config.scenario,
            baseyear=config.baseyear,
            pyear_start=config.pyear_start,
            pyear_end=config.pyear_end,
            pyear_step=config.pyear_step,
            nsamps=config.nsamps,
            location_file=config.location_file
            or config.other_top_level_values.get("location_file"),
        )


TOP_LEVEL_PARAM_NAMES: frozenset[str] = frozenset(
    f.name for f in fields(TopLevelParams)
)
