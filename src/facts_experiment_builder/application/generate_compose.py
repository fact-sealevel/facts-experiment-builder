#!/usr/bin/env python3
"""Generate Docker Compose file from experiment metadata.

This script follows a domain-driven design pattern:
- experiment-config.yaml is the "user interface" (UI layer)
- Module service specs are created from experiment metadata (Adapter layer)
- Docker compose files are the "engine" (Infrastructure layer)

Usage:
    python -m facts_experiment_builder.application.generate_compose <experiment_dir>

"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from facts_experiment_builder.core.module.module_service_spec import (
    get_experiment_paths,
    build_module_service_spec,
)
from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.core.module.module_service_spec import ModuleServiceSpec

from facts_experiment_builder.core.workflow.workflow import (
    Workflow,
    workflows_from_metadata,
)

from facts_experiment_builder.infra.path_utils import expand_path
from facts_experiment_builder.core.module.module_schema import (
    collect_metadata_param_keys,
    ModuleSchema,
)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SUCCESS = 25  # custom level between INFO (20) and WARNING (30); must match CLI handler

_REQUIRED_FIELDS = [
    "experiment_name",
    "pipeline-id",
    "nsamps",
    "scenario",
    "pyear_start",
    "pyear_end",
    "pyear_step",
    "baseyear",
    "module-specific-input-data",
    "shared-input-data",
    "output-data-location",
]


@dataclass(frozen=True)
class _ExperimentPlan:
    """Result of phase 1: parsed experiment structure and module name lists."""

    experiment: FactsExperiment
    temperature_module_name: Optional[str]  # TODO rename to climate
    sealevel_module_names: List[str]
    framework_module_names: List[str]
    esl_module_names: List[str]
    suppress_output_types: Set[str]
    workflows: Dict[str, Workflow]


@dataclass(frozen=True)
class _ModuleSpecs:
    """Result of phase 2: all created ModuleServiceSpec instances."""

    temperature_module: Optional[ModuleServiceSpec]
    sealevel_modules: Dict[str, ModuleServiceSpec]
    framework_modules: Dict[str, ModuleServiceSpec]
    esl_modules: Dict[str, ModuleServiceSpec]
    #TODO do not want these categories to be so rigid in the future


def _log_success(msg: str, *args: object) -> None:
    logger.log(_SUCCESS, msg, *args)


def _extract_all_module_names_from_manifest(metadata: Dict[str, Any]) -> List[str]:
    """Extract a flat list of all module names from the experiment manifest keys."""
    names: List[str] = []
    temp = metadata.get("temperature_module")
    if temp and str(temp).upper() != "NONE":
        names.append(str(temp))
    for m in metadata.get("sealevel_modules") or []:
        if isinstance(m, str):
            names.append(m)
    for m in metadata.get("framework_modules") or []:
        if isinstance(m, str):
            names.append(m)
    for m in metadata.get("esl_modules") or []:
        if isinstance(m, str):
            names.append(m)
    return names


def _validate_climate_file_inputs(
    metadata: Dict[str, Any],
    sealevel_modules: List[str],
    schemas: Dict[str, ModuleSchema],
) -> None:
    """Validate that sealevel modules have climate file inputs when no temperature module is specified.

    Pure logic — accepts pre-loaded schemas. Raises ValueError listing any modules
    that require a climate file but have no value provided in metadata.
    """
    missing_climate_files = []

    for module_name in sealevel_modules:
        module_schema = schemas[module_name]

        if not module_schema.uses_climate_file:
            continue

        module_inputs = metadata.get(module_name, {}).get("inputs", {})
        climate_input_keys = module_schema.get_output_volume_input_keys()

        climate_file = next(
            (
                v
                for k in climate_input_keys
                if (v := module_inputs.get(k)) and (not isinstance(v, str) or v.strip())
            ),
            None,
        )

        if not climate_file:
            missing_climate_files.append(module_name)

    if missing_climate_files:
        raise ValueError(
            f"No temperature module specified, but the following sealevel modules are missing "
            f"climate file inputs: {', '.join(missing_climate_files)}. "
            f"Please provide the climate file input (e.g. 'climate_data_file' or the module-specific "
            f"input key) in the inputs section for each sealevel module."
        )


def _collect_workflow_output_paths_by_type(
    metadata: Dict[str, Any],
    wf: Workflow,
    output_type: str,
    schemas: Dict[str, "ModuleSchema"],
    *,
    container_prefix: str = "/mnt/total_out",
) -> List[str]:
    """
    Collect container paths for workflow module outputs that match the given output_type
    and have pass_to_total=True in their module schema.

    For each module in the workflow, reads metadata[mod].outputs; each value must be
    a dict with "value" and "output_type". If a module schema is present in `schemas`,
    only outputs whose OutputFileSpec has pass_to_total=True are included. Outputs from
    modules not found in `schemas` are included for backward compatibility.
    """
    paths: List[str] = []
    prefix = container_prefix.rstrip("/")

    for mod in wf.module_names:
        out_section = metadata.get(mod, {}) or {}
        if not isinstance(out_section, dict):
            continue
        outputs = out_section.get("outputs") or {}
        if not isinstance(outputs, dict):
            continue

        schema = schemas.get(mod)
        pass_to_total_by_name: Dict[str, bool] = {}
        if schema is not None:
            pass_to_total_by_name = {
                o["name"]: o.get("pass_to_total", True)
                for o in schema.get_file_outputs()
            }

        for key, v in outputs.items():
            if isinstance(v, dict) and "value" in v:
                p = v.get("value") or ""
                ot = v.get("output_type", "")
            else:
                continue

            if not (p and isinstance(p, str) and ot == output_type):
                continue

            if pass_to_total_by_name and not pass_to_total_by_name.get(key, True):
                logger.info(
                    "%s output '%s': pass_to_total=false, skipping.",
                    mod,
                    key,
                )
                continue

            paths.append(f"{prefix}/{p.strip()}")
    return paths


def _build_facts_total_section_for_workflow(
    wf: Workflow,
    facts_total_image: str,
    output_type: str,
) -> Dict[str, Any]:
    """Build the synthetic metadata section for a facts-total workflow service with empty inputs.item and type-specific output-path."""
    return {
        "inputs": {"item": []},
        "outputs": {"output-path": wf.total_output_filename_for_type(output_type)},
        "options": {},
        "fingerprint_params": {},
        "image": facts_total_image,
        "_output_subdir": "facts-total",
        "_output_container_base": "/mnt/total_out/facts-total",
    }


def _populate_section_with_global_outputs(
    section: Dict[str, Any],
    metadata: Dict[str, Any],
    wf: Workflow,
    schemas: Dict[str, "ModuleSchema"],
) -> None:
    """Extend section["inputs"]["item"] with container paths for outputs with output_type "global"."""
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "global", schemas)
    section["inputs"]["item"].extend(paths)


def _populate_section_with_local_outputs(
    section: Dict[str, Any],
    metadata: Dict[str, Any],
    wf: Workflow,
    schemas: Dict[str, "ModuleSchema"],
) -> None:
    """Extend section["inputs"]["item"] with container paths for outputs with output_type "local"."""
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "local", schemas)
    section["inputs"]["item"].extend(paths)


def _create_facts_total_compose_service(
    section: Dict[str, Any],
    service_name: str,
    wf: Workflow,
    metadata: Dict[str, Any],
    experiment_dir: Path,
    known_module_names: List,
    schema: ModuleSchema,
) -> Dict[str, Any]:
    """Build the compose service dict for a facts-total workflow from its synthetic section."""
    metadata_copy = dict(metadata)
    metadata_copy[service_name] = section

    wf_module = build_module_service_spec(
        metadata=metadata_copy,
        module_name=service_name,
        known_module_names=known_module_names,
        module_definition=schema,
    )
    compose_service = wf_module.generate_compose_service()
    compose_service["depends_on"] = {
        mod: {"condition": "service_completed_successfully"} for mod in wf.module_names
    }
    return compose_service


def check_metadata_has_required_fields(metadata_obj, required_fields):
    """This function accepts a list of required fields and a metadata object and subsets the metadata to required fields."""
    # Subset
    required_fields_meta = {
        k: v for k, v in metadata_obj.items() if k in required_fields
    }

    # R aise error if any are missing a value
    for k, v in required_fields_meta.items():
        if v is None:
            raise ValueError(
                f"A value for {k} is required but none was found. Check that all required fields in this experiment's experiment-config.yml have been completed."
            )

    return None


def extract_experiment_dir_from_metadata_path(metadata_path):
    """This function extracts the experiment directory from the metadata path obj"""

    experiment_dir = metadata_path.parent
    if experiment_dir == metadata_path:
        raise ValueError(
            f"No experiment dir found in the parent path of provided metadata path, {metadata_path}"
        )
    return experiment_dir


def _make_experiment_plan(
    metadata: Dict[str, Any], schemas: Dict[str, ModuleSchema]
) -> _ExperimentPlan:
    """Phase 1 of generating compose:
    Validate metadata and build a typed experiment plan.

    Ths fn is only data transformation, there should be no filesystem I/O.
    """

    # This should raise an error if user has not completed necessary fields in experiment-config.yaml
    check_metadata_has_required_fields(
        metadata_obj=metadata, required_fields=_REQUIRED_FIELDS
    )

    # Get the list of modules included in experiment from manifest in exp config
    _manifest_module_names = _extract_all_module_names_from_manifest(metadata)

    # Use list of modules to load schema for each module
    list_of_schemas = list(schemas.values())
    # Get keys for top level params and fingerprint params from each module in experiment
    _top_level_keys = set(collect_metadata_param_keys(list_of_schemas, "top_level"))
    _fp_keys = set(collect_metadata_param_keys(list_of_schemas, "fingerprint_params"))

    # Create FactsExperiment obj from metadata dict
    experiment = FactsExperiment.from_metadata_dict(
        metadata,
        top_level_keys=_top_level_keys,
        fingerprint_keys=_fp_keys,
    )
    # Set output (local or global) based on user spec. in experiment config
    suppress_output_types: Set[str] = (
        {"local"} if experiment.projection_scale == "global" else set()
    )
    # Separate module names by step
    temperature_module_name = experiment.climate_step.module_name or "NONE"
    sealevel_module_names = experiment.sealevel_step.module_names
    framework_module_names = (
        [experiment.totaling_step.module_name]
        if experiment.totaling_step.is_present
        else []
    )
    esl_module_names = (
        [experiment.extreme_sealevel_step.module_name]
        if experiment.extreme_sealevel_step.is_present
        else []
    )
    # Make workflow obj from metadata
    workflows = workflows_from_metadata(metadata)

    # Make an ExperimentPlan obj
    # (first component of generate compose, used to build module spec objs)
    return _ExperimentPlan(
        experiment=experiment,
        temperature_module_name=temperature_module_name,
        sealevel_module_names=sealevel_module_names,
        framework_module_names=framework_module_names,
        esl_module_names=esl_module_names,
        suppress_output_types=suppress_output_types,
        workflows=workflows,
    )


def _build_module_specs(
    plan: _ExperimentPlan,
    metadata: Dict[str, Any],
    schemas: Dict,
    known_module_names: List,
) -> _ModuleSpecs:
    """Phase 2: Create a ModuleServiceSpec for each module in the experiment.

    All filesystem I/O for module YAML loading is isolated here.
    """
    temperature_module: Optional[ModuleServiceSpec] = None
    sealevel_modules: Dict[str, ModuleServiceSpec] = {}
    framework_modules: Dict[str, ModuleServiceSpec] = {}
    esl_modules: Dict[str, ModuleServiceSpec] = {}

    temp_module_definition = schemas[plan.temperature_module_name]
    if plan.temperature_module_name.upper() != "NONE":
        temp_module_name = plan.temperature_module_name
        temperature_module = build_module_service_spec(
            metadata=metadata,
            module_name=temp_module_name,
            known_module_names=known_module_names,
            module_definition=temp_module_definition,
        )
        _log_success("Created %s module", plan.temperature_module_name)
    else:
        logger.info("No temperature module specified (NONE)")

        _validate_climate_file_inputs(
            metadata=metadata, sealevel_modules=sealevel_modules, schemas=schemas
        )

    for module_name in plan.sealevel_module_names:
        module_schema = schemas[module_name]

        sealevel_modules[module_name] = build_module_service_spec(
            metadata=metadata,
            module_name=module_name,
            known_module_names=known_module_names,
            module_definition=module_schema,
        )
        _log_success("Created %s module", module_name)

    for module_name in plan.framework_module_names:
        if schemas[module_name].per_workflow and plan.workflows:
            continue
        schema = schemas[module_name]
        framework_modules[module_name] = build_module_service_spec(
            metadata=metadata,
            module_name=module_name,
            known_module_names=known_module_names,
            module_definition=schema,
        )

        _log_success("Created %s module", module_name)

    for module_name in plan.esl_module_names:
        schema = schemas[module_name]
        esl_modules[module_name] = build_module_service_spec(
            metadata=metadata,
            module_name=module_name,
            known_module_names=known_module_names,
            module_definition=schema,
        )

        _log_success("Created %s module", module_name)

    # Make _ModuleSpecs obj
    # This is what's returned by _build_module_specs
    # and used by _build_compose_servies()
    specs = _ModuleSpecs(
        temperature_module=temperature_module,
        sealevel_modules=sealevel_modules,
        framework_modules=framework_modules,
        esl_modules=esl_modules,
    )

    if not any(
        [
            specs.temperature_module,
            specs.sealevel_modules,
            specs.framework_modules,
            specs.esl_modules,
        ]
    ):
        has_step_data = bool(
            metadata.get("supplied-totaled-sealevel-step-data")
            or metadata.get("experiment-specific-input-data")
        )
        if not has_step_data:
            raise ValueError(
                "No modules could be created from metadata. "
                "Please ensure at least one module is specified and has valid configuration."
            )
        logger.info(
            "All experiment steps use pre-existing data. No Docker services to generate."
        )

    return specs


def _create_esl_workflow_services(
    esl_module_names: List[str],
    workflows: Dict[str, Workflow],
    metadata: Dict[str, Any],
    experiment_dir: Path,
    projection_scale: Optional[str],
    schemas: Dict[str, ModuleSchema],
) -> Dict[str, Any]:
    """Build one ESL compose service per workflow, keyed by service name."""
    services: Dict[str, Any] = {}
    known_module_names = list(schemas.keys())
    if not esl_module_names:
        return services
    if projection_scale == "global":
        logger.info("Skipping per-workflow ESL services (projection_scale=global)")
        return services

    for module_name in esl_module_names:
        schema = schemas[module_name]

        base_section = metadata.get(module_name) or {}
        if not isinstance(base_section, dict):
            base_section = {}
        try:
            exp_paths = get_experiment_paths(metadata, f"{module_name} module")
            module_specific_base = expand_path(
                exp_paths.get("module_specific_input_data"),
                "module-specific-input-data",
            )
        except (KeyError, TypeError):
            module_specific_base = ""
        for _wf_name, wf in workflows.items():
            service_name = f"{module_name}-{wf.name}"
            base_inputs = dict(base_section.get("inputs") or {})
            base_inputs["total_localsl_file"] = wf.total_localsl_path_under_output
            gesla_val = base_inputs.get("gesla_dir")
            if not gesla_val or (
                isinstance(gesla_val, dict) and gesla_val.get("value") in (None, "")
            ):
                if module_specific_base:
                    base_inputs["gesla_dir"] = (
                        f"{module_specific_base}/{module_name}/gesla_data"
                    )
            base_outputs = base_section.get("outputs") or {}
            synthetic_section = {
                **base_section,
                "inputs": base_inputs,
                "outputs": {**base_outputs, "output-dir": "."},
            }
            metadata_copy = dict(metadata)
            metadata_copy[service_name] = synthetic_section

            esl_module = build_module_service_spec(
                metadata=metadata_copy,
                module_name=service_name,
                known_module_names=known_module_names,
                module_definition=schema,
            )
            compose_svc = esl_module.generate_compose_service()
            compose_svc["depends_on"] = {
                wf.facts_total_service_name_for_type("local"): {
                    "condition": "service_completed_successfully"
                }
            }
            services[service_name] = compose_svc
            _log_success("Created %s ESL workflow service", service_name)
    return services


def _build_standard_services(specs: _ModuleSpecs, plan: _ExperimentPlan) -> Dict:
    """Given a _ModuleSpecs and _ExperimentPlan obj, build dict of compose services
    for climate and sealevel steps (where 1 module = 1 service).

    Return"""
    services = {}

    temperature_service_name = (
        specs.temperature_module.module_name if specs.temperature_module else None
    )
    if specs.temperature_module:
        services[temperature_service_name] = (
            specs.temperature_module.generate_compose_service()
        )

    for _module_name, module in specs.sealevel_modules.items():
        service_name = module.module_name
        services[service_name] = module.generate_compose_service(
            temperature_service_name=temperature_service_name,
            suppress_output_types=plan.suppress_output_types,
        )
    return services


def _build_per_workflow_services(plan, metadata, experiment_dir, schemas):
    services = {}

    facts_total_name = next(
        (m for m in plan.framework_module_names if schemas[m].per_workflow),
        "facts-total",
    )
    facts_total_schema = schemas[facts_total_name]
    facts_total_container_image = facts_total_schema.container_image

    for wf_name, wf in plan.workflows.items():
        for output_type in facts_total_schema.output_types:
            if output_type == "local" and plan.experiment.projection_scale == "global":
                logger.info(
                    "Skipping local facts-total for %s (projection_scale=global)",
                    wf_name,
                )
                continue
            section = _build_facts_total_section_for_workflow(
                wf, facts_total_container_image, output_type
            )
            if output_type == "global":
                _populate_section_with_global_outputs(
                    section, metadata, wf, schemas=schemas
                )
            else:
                _populate_section_with_local_outputs(
                    section, metadata, wf, schemas=schemas
                )
            service_name = wf.facts_total_service_name_for_type(output_type)
            compose_svc = _create_facts_total_compose_service(
                section=section,
                service_name=service_name,
                wf=wf,
                metadata=metadata,
                schema=facts_total_schema,
                experiment_dir=experiment_dir,
                known_module_names=frozenset(schemas.keys()),
            )
            services[service_name] = compose_svc
            _log_success("Created %s workflow service", service_name)

    services.update(
        _create_esl_workflow_services(
            esl_module_names=plan.esl_module_names,
            workflows=plan.workflows,
            metadata=metadata,
            experiment_dir=experiment_dir,
            projection_scale=plan.experiment.projection_scale,
            schemas=schemas,
        )
    )
    return services


def _build_compose_services(
    specs: _ModuleSpecs,
    plan: _ExperimentPlan,
    metadata: Dict[str, Any],
    experiment_dir: Path,
    schemas: Dict[str, ModuleSchema],
) -> Dict[str, Any]:
    """Phase 3: Render ModuleServiceSpecs into Docker Compose service dicts."""
    services = {}

    services.update(_build_standard_services(specs, plan))
    if plan.workflows:
        services.update(
            _build_per_workflow_services(plan, metadata, experiment_dir, schemas)
        )

    if not plan.workflows and plan.experiment.projection_scale != "global":
        for _esl_name, esl_module in specs.esl_modules.items():
            service_name = esl_module.module_name
            services[service_name] = esl_module.generate_compose_service()
            _log_success("Created %s module", service_name)

    return services


def generate_compose(
    metadata: Dict[str, Any], experiment_dir: Path, definition
) -> Dict[str, Any]:
    """
    Generate Docker Compose dict from already-loaded experiment metadata.

    Args:
        metadata: Loaded experiment-config.yaml as a dict
        experiment_dir: Path to the experiment directory

    Returns:
        Complete Docker Compose file dictionary
    """
    # TODO: in future, should probably make a dataclass or similar for experiment metadata dict so that
    # can just access an attr instead of needing fns to get names from manifest etc?

    #  setup - only references to definition are here
    module_names = _extract_all_module_names_from_manifest(metadata)
    schemas = {m_name: definition.get_schema(m_name) for m_name in set(module_names)}
    known_module_names = definition.module_names()

    # Make experiment plan
    plan = _make_experiment_plan(metadata, schemas)
    specs = _build_module_specs(
        plan=plan,
        metadata=metadata,
        schemas=schemas,
        known_module_names=known_module_names,
    )
    if not any(
        [
            specs.temperature_module,
            specs.sealevel_modules,
            specs.framework_modules,
            specs.esl_modules,
        ]
    ):
        return {"services": {}}
    services = _build_compose_services(
        specs,
        plan,
        metadata,
        experiment_dir,
        schemas=schemas,
    )
    return {"services": services}
