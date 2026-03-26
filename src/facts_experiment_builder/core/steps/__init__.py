from typing import Any, Dict, Tuple

from facts_experiment_builder.core.steps.base import ExperimentStep
from facts_experiment_builder.core.steps.climate_step import ClimateStep
from facts_experiment_builder.core.steps.sealevel_step import SealevelStep
from facts_experiment_builder.core.steps.totaling_step import TotalingStep
from facts_experiment_builder.core.steps.extreme_sealevel_step import (
    ExtremeSealevelStep,
)

__all__ = [
    "ExperimentStep",
    "ClimateStep",
    "SealevelStep",
    "TotalingStep",
    "ExtremeSealevelStep",
    "steps_from_metadata",
]


def steps_from_metadata(
    manifest: Dict[str, Any],
    module_sections: Dict[str, Any],
) -> Tuple[ClimateStep, SealevelStep, TotalingStep, ExtremeSealevelStep]:
    """Build all four step objects from a parsed manifest and module_sections dict."""
    temp_module_name = manifest.get("temperature_module")
    if temp_module_name and str(temp_module_name).upper() != "NONE":
        climate_step = ClimateStep.from_dict(
            temp_module_name, module_sections.get(temp_module_name) or {}
        )
    else:
        climate_step = ClimateStep.none_step()

    sealevel_names = manifest.get("sealevel_modules") or []
    if isinstance(sealevel_names, str):
        sealevel_names = [sealevel_names]
    sealevel_step = SealevelStep.from_dict(sealevel_names, module_sections)

    fw_modules = manifest.get("framework_modules") or []
    totaling_module = fw_modules[0] if fw_modules else None
    totaling_step = TotalingStep.from_dict(
        totaling_module,
        module_sections.get(totaling_module) or {} if totaling_module else {},
    )

    esl_modules = manifest.get("esl_modules") or []
    if isinstance(esl_modules, str):
        esl_modules = [esl_modules]
    esl_module = esl_modules[0] if esl_modules else None
    extreme_sealevel_step = ExtremeSealevelStep.from_dict(
        esl_module,
        module_sections.get(esl_module) or {} if esl_module else {},
    )

    return climate_step, sealevel_step, totaling_step, extreme_sealevel_step
