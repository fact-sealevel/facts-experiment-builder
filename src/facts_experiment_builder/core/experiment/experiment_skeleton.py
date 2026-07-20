"""Intent data for a new experiment, built from CLI inputs before YAML loading."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
)


def is_totaling_needed(sealevel_step: str) -> bool:
    sealevel_module_ls = parse_module_list_str(s=sealevel_step)

    return len(sealevel_module_ls) > 1


def parse_module_regions(module_regions_args: tuple) -> Dict[str, List[str]]:
    """Parse a tuple of 'module-name=R1,R2' strings into {module: [regions]}.

    Accepts the raw value from a Click multiple=True option.
    Example: ("emulandice2-glaciers=RGI01,RGI02",) -> {"emulandice2-glaciers": ["RGI01", "RGI02"]}
    """
    result: Dict[str, List[str]] = {}
    for entry in module_regions_args or ():
        if "=" not in entry:
            raise ValueError(
                f"Invalid --module-regions format '{entry}'. "
                "Expected 'module-name=REGION1,REGION2'."
            )
        module_name, regions_str = entry.split("=", 1)
        regions = [r.strip() for r in regions_str.split(",") if r.strip()]
        if not regions:
            raise ValueError(
                f"No regions specified for module '{module_name}' in --module-regions."
            )
        result[module_name.strip()] = regions
    return result


@dataclass(frozen=True)
class ExperimentSkeleton:
    """Captures module names / data paths and workflows from CLI inputs.

    Created in the CLI before workflow collection and before any module YAMLs are
    loaded.  Pass to ``hydrate_experiment()`` in the application layer to produce a
    fully-formed ``FactsExperiment``.
    """

    climate_module: Optional[str] = None  # None if data provided
    climate_data: Optional[str] = None  # None if module provided
    sealevel_modules: List[str] = None  # [] if data provided
    supplied_totaled_sealevel_step_data: Optional[str] = (
        None  # None if modules provided
    )
    totaling_module: Optional[str | None] = None  # None if no totaling step
    extremesealevel_module: Optional[str] = None  # None if no ESL step
    workflows: Dict[str, str] = field(default_factory=dict)
    module_regions: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def from_inputs(
        cls,
        climate_step: Optional[str],
        supplied_climate_step_data: Optional[str],
        sealevel_step: Optional[str],
        supplied_totaled_sealevel_step_data: Optional[str],
        extremesealevel_step: Optional[str],
        module_regions: Optional[Dict[str, List[str]]] = None,
    ) -> "ExperimentSkeleton":
        """Build a skeleton by parsing comma-separated CLI module strings."""
        from facts_experiment_builder.core.experiment.module_name_validation import (
            parse_module_list_str,
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

        climate_modules = parse_module_list_str(climate_step)
        sealevel_modules = parse_module_list_str(sealevel_step)
        esl_modules = parse_module_list_str(extremesealevel_step)

        # Domain rules:
        # - totaling can't run if sealevel step bypassed
        # - totaling doesn't run if no sealevel modules are passed
        # - totaling runs if more than one sealevel module included
        if supplied_totaled_sealevel_step_data or not sealevel_modules:
            totaling_module = None
        else:
            totaling_module = "facts-total"
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
            totaling_module=totaling_module,
            extremesealevel_module=esl_modules[0] if esl_modules else None,
            module_regions=module_regions or {},
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
