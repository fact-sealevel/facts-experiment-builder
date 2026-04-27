"""Intent data for a new experiment, built from CLI inputs before YAML loading."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ExperimentSkeleton:
    """Captures module names / data paths and workflows from CLI inputs.

    Created in the CLI before workflow collection and before any module YAMLs
    are loaded.  Pass to ``hydrate_experiment()`` in the application layer to
    produce a fully-formed ``FactsExperiment``.
    """

    climate_module: Optional[str] = None  # None if data provided
    climate_data: Optional[str] = None  # None if module provided
    sealevel_modules: List[str] = None  # [] if data provided
    supplied_totaled_sealevel_step_data: Optional[str] = (
        None  # None if modules provided
    )
    totaling_module: Optional[str] = None  # None if no totaling step
    extremesealevel_module: Optional[str] = None  # None if no ESL step
    workflows: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_cli_inputs(
        cls,
        climate_step: Optional[str],
        supplied_climate_step_data: Optional[str],
        sealevel_step: Optional[str],
        supplied_totaled_sealevel_step_data: Optional[str],
        extremesealevel_step: Optional[str],
    ) -> "ExperimentSkeleton":
        """Build a skeleton by parsing comma-separated CLI module strings."""
        from facts_experiment_builder.core.experiment.module_name_validation import (
            parse_module_list,
        )

        # validate climate step inputs
        if not supplied_totaled_sealevel_step_data:
            if climate_step and supplied_climate_step_data:
                raise ValueError(
                    "Pass either a climate module (--climate-step) or climate data "
                    "(--supplied-climate-step-data), not both."
                )
            if not climate_step and not supplied_climate_step_data:
                raise ValueError(
                    "Must pass either a climate module (--climate-step) or climate data "
                    "(--supplied-climate-step-data)."
                )
        # validate sealevel step data
        if sealevel_step and supplied_totaled_sealevel_step_data:
            raise ValueError(
                "Pass either sea-level modules (--sealevel-step) or totaled sea-level data "
                "(--supplied-totaled-sealevel-step-data), not both."
            )

        climate_modules = parse_module_list(climate_step)
        sealevel_modules = parse_module_list(sealevel_step)
        esl_modules = parse_module_list(extremesealevel_step)

        # Domain rules:
        # - totaling can't run if sealevel step bypassed
        # - totaling doesn't run if no sealevel modules are passed
        # - totaling runs if more than one sealevel module included
        if supplied_totaled_sealevel_step_data:
            totaling_module = None
        if not supplied_totaled_sealevel_step_data and not sealevel_modules:
            totaling_module = None
        elif sealevel_modules:
            if len(sealevel_modules) >= 1:
                totaling_module = "facts-total"
        return cls(
            climate_module=climate_modules[0] if climate_modules else None,
            climate_data=supplied_climate_step_data,
            sealevel_modules=sealevel_modules,
            supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
            totaling_module= totaling_module, #totaling_modules[0] if totaling_modules else None,
            extremesealevel_module=esl_modules[0] if esl_modules else None,
        )

    @property
    def all_module_names(self) -> List[str]:
        """All module names across all steps (excludes data-only steps)."""
        names: List[str] = []
        if self.climate_module:
            names.append(self.climate_module)
        names.extend(self.sealevel_modules)
        if self.totaling_module:
            names.append(self.totaling_module)
        if self.extremesealevel_module:
            names.append(self.extremesealevel_module)
        return names
