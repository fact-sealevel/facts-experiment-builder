"""Module to hold class, functions related to experiment config object before written to
yaml."""

from dataclasses import dataclass
from typing import Iterable

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.experiment.experiment import FactsExperiment
from facts_experiment_builder.core.steps.base import ExperimentStep

_CONFIG_SCHEMA_VERSION = 2  # bump when experiment-config.yaml's shape changes


@dataclass(frozen=True)
class ExperimentConfig:
    """Data class to hold all information needed for an experiment config file.

    This maps between FactsExperiment and the jinja2 template for experiment-
    config.yaml.
    """

    experiment_name: str
    date_created: str
    projection_scale: str
    manifest: dict
    workflows: dict
    paths: dict
    top_level_params: dict
    module_sections: dict  # Need to define what this is more clearly. This is the dict of all of the module-specific sections (built from ModuleExeprimentSpec) in 2nd half of config
    included_modules: list  # this is list of modules that apperas in top of config
    inputs: list  # inputs section at top of config
    outputs: list  # outputs section at top of config
    module_keys: list  # this is a list of all the modules that have sections in second part of config--need to cleanup how its made
    module_registry_version: str
    config_schema_version: int = _CONFIG_SCHEMA_VERSION


@dataclass(frozen=True)
class ExperimentManifest:
    """Data class to hold manifest.

    Manifest is built from facts exp file and used in creation of experiment config.
    Uses step objs from FactsExperiment. TODO dont hard code these names.
    """

    climate_module: str  # should this be list/tuple?
    sealevel_modules: list
    framework_modules: tuple
    esl_modules: tuple


def build_module_sections(steps: Iterable[ExperimentStep]) -> dict[str, dict]:
    """Build the per-module sections of experiment-config.yaml.

    Each spec's to_dict() nests two parts: `values` (the resolved, human-editable
    inputs/options/outputs/fingerprint_params/image) and `schema` (the frozen module
    definition consulted from the registry at setup-experiment time) — see
    ModuleExperimentSpec.to_dict().
    """
    return {
        spec.module_name: spec.to_dict()
        for step in steps
        for spec in step.module_specs()
    }


def make_included_modules_section(manifest: dict) -> list:
    """Function to make 'included modules section' of experiment config from manifest.

    TODO this needs to be reworked/is it necessarY?
    """
    included_modules = []
    if "climate_module" in manifest:
        included_modules.append("climate_module")
    if "sealevel_modules" in manifest:
        included_modules.append("sealevel_modules")
    if "framework_modules" in manifest and manifest["framework_modules"]:
        included_modules.append("framework_modules")
    if "esl_modules" in manifest and manifest["esl_modules"]:
        included_modules.append("esl_modules")
    return included_modules


def make_inputs_section(experiment_obj: FactsExperiment) -> list:
    """Function to make inputs section of experiment config from experiment obj."""
    inputs = []
    if "module-specific-input-data" in experiment_obj.paths:
        inputs.append("module-specific-input-data")
    if "shared-input-data" in experiment_obj.paths:
        inputs.append("shared-input-data")
    if "experiment-specific-input-data" in experiment_obj.paths:
        inputs.append("experiment-specific-input-data")
    if "supplied-totaled-sealevel-step-data" in experiment_obj.paths:
        inputs.append("supplied-totaled-sealevel-step-data")
    return inputs


def make_outputs_section(experiment_obj) -> list:
    # Outputs section (output-data-location)
    outputs = []
    if "output-data-location" in experiment_obj.paths:
        outputs.append("output-data-location")
    return outputs


def make_module_keys(
    experiment_obj: FactsExperiment,
    manifest: dict,
    included_modules: list,
    inputs: list,
    outputs: list,
    module_sections: list,
) -> list:
    # Module-specific sections (all keys that are module names)
    # Exclude top-level params, included_modules, inputs, outputs, and experiment_name
    excluded_keys = (
        set(experiment_obj.top_level_params.keys())
        | set(experiment_obj.fingerprint_params.keys())
        | set(included_modules)
        | set(inputs)
        | set(outputs)
        | {"experiment_name"}
    )
    module_keys = [
        key
        for key in module_sections.keys()
        if key not in excluded_keys and isinstance(module_sections[key], dict)
    ]

    # Sort module_keys so climate_module appears first if it exists
    climate_module_name = manifest.get("climate_module")
    if (
        climate_module_name
        and isinstance(climate_module_name, str)
        and climate_module_name.upper() != "NONE"
    ):
        if climate_module_name in module_keys:
            module_keys.remove(climate_module_name)
            module_keys.insert(0, climate_module_name)

    return module_keys


def facts_experiment_to_config(
    experiment_obj: FactsExperiment,
    module_registry_version: str | None = None,
):
    # Get totaling, esl module names, if present
    # climate_modules = (
    #      [experiment_obj.climate_step.module_name]
    #      if experiment_obj.climate_step.is_present
    #      else []
    # )

    framework_modules = (
        [experiment_obj.totaling_step.module_name]
        if experiment_obj.totaling_step.is_present
        else []
    )
    esl_module = (
        [experiment_obj.extreme_sealevel_step.module_name]
        if experiment_obj.extreme_sealevel_step.is_present
        else []
    )
    # make manifest
    manifest = {
        "climate_module": experiment_obj.climate_step.module_name
        or "NONE",  # climate_modules,
        "sealevel_modules": experiment_obj.sealevel_step.module_names,
        "framework_modules": framework_modules,
        "esl_modules": esl_module,
    }

    # Make dict of module sections
    # This is the dict of all of the module-specific sections (built from ModuleExeprimentSpec) in 2nd half of config
    module_sections = build_module_sections(experiment_obj.list_all_steps())

    inputs = make_inputs_section(experiment_obj)

    outputs = make_outputs_section(experiment_obj)

    included_modules = make_included_modules_section(manifest=manifest)
    module_keys = make_module_keys(
        experiment_obj=experiment_obj,
        manifest=manifest,
        included_modules=included_modules,
        inputs=inputs,
        outputs=outputs,
        module_sections=module_sections,
    )
    return ExperimentConfig(
        manifest=manifest,
        workflows=experiment_obj.workflows,
        experiment_name=experiment_obj.experiment_name,
        date_created=experiment_obj.date_created,
        projection_scale=experiment_obj.projection_scale,
        top_level_params=experiment_obj.top_level_params,
        module_sections=module_sections,
        included_modules=included_modules,
        inputs=inputs,
        outputs=outputs,
        paths=experiment_obj.paths,
        module_keys=module_keys,
        module_registry_version=module_registry_version,
    )
