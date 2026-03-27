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

    climate_module: Optional[str]  # None if data provided
    climate_data: Optional[str]  # None if module provided
    sealevel_modules: List[str]  # [] if data provided
    supplied_totaled_sealevel_step_data: Optional[str]  # None if modules provided
    totaling_module: Optional[str]  # None if no totaling step
    extremesealevel_module: Optional[str]  # None if no ESL step
    workflows: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_cli_inputs(
        cls,
        climate_step: Optional[str],
        supplied_climate_step_data: Optional[str],
        sealevel_step: Optional[str],
        supplied_totaled_sealevel_step_data: Optional[str],
        totaling_step: Optional[str],
        extremesealevel_step: Optional[str],
    ) -> "ExperimentSkeleton":
        """Build a skeleton by parsing comma-separated CLI module strings."""
        from facts_experiment_builder.core.experiment.module_name_validation import (
            parse_module_list,
        )

        climate_modules = parse_module_list(climate_step)
        sealevel_modules = parse_module_list(sealevel_step)
        totaling_modules = parse_module_list(totaling_step)
        esl_modules = parse_module_list(extremesealevel_step)

        return cls(
            climate_module=climate_modules[0] if climate_modules else None,
            climate_data=supplied_climate_step_data,
            sealevel_modules=sealevel_modules,
            supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
            totaling_module=totaling_modules[0] if totaling_modules else None,
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
