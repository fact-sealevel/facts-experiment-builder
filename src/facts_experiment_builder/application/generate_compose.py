#!/usr/bin/env python3
"""Generate Docker Compose file from experiment metadata.

This script follows a domain-driven design pattern:
- experiment-config.yaml is the "user interface" (UI layer)
- Module service specs are created from experiment metadata (Adapter layer)
- Docker compose files are the "engine" (Infrastructure layer)

Usage:
    python -m facts_experiment_builder.application.generate_compose <experiment_dir>

"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from facts_experiment_builder.adapters.module_adapter import (
    create_module_service_spec_from_metadata,
)
from facts_experiment_builder.adapters.adapter_utils import get_experiment_paths
from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.core.module.module_service_spec import ModuleServiceSpec
from facts_experiment_builder.core.registry import ModuleRegistry
from facts_experiment_builder.core.workflow.workflow import (
    Workflow,
    workflows_from_metadata,
)

# from facts_experiment_builder.infra.path_manager import find_module_yaml_path
from facts_experiment_builder.infra.path_utils import expand_path
from facts_experiment_builder.infra.experiment_loader import load_experiment_metadata
from facts_experiment_builder.infra.module_loader import (
    load_module_schema_by_name,
    load_module_schema_from_yaml,
)
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
    temperature_module_name: Optional[str]
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


def _module_requires_climate_file(module_name: str, registry: ModuleRegistry) -> bool:
    """
    Check if a module requires a climate file by loading its module YAML configuration.

    Args:
        module_name: Name of the module (e.g., 'bamber19-icesheets')

    Returns:
        True if climate_file_required is True in module YAML, False otherwise
    """

    # Get path
    module_yaml_path = registry.get_module_yaml_path(module_name)
    # Load module yaml
    module_yaml = load_module_schema_from_yaml(yaml_path=module_yaml_path)
    # Return uses climate file attr
    return module_yaml.uses_climate_file


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


def _load_schemas(
    sealevel_modules: List[str],
    registry: ModuleRegistry,
) -> Dict[str, ModuleSchema]:
    """I/O wrapper: load module schemas.
    Return dick of schemas."""
    schemas = {
        m: load_module_schema_from_yaml(registry.get_module_yaml_path(m))
        for m in sealevel_modules
    }
    return schemas


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


def _module_is_per_workflow(module_name: str, registry: ModuleRegistry) -> bool:
    """Return True if the module YAML declares per_workflow: true."""
    try:
        module_yaml_path = registry.get_module_yaml_path(module_name)
        with open(module_yaml_path) as f:
            cfg = yaml.safe_load(f) or {}
        return bool(cfg.get("per_workflow"))
    except FileNotFoundError:
        return False


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
    facts_total_yaml_path: Path,
) -> Dict[str, Any]:
    """Build the compose service dict for a facts-total workflow from its synthetic section."""
    metadata_copy = dict(metadata)
    metadata_copy[service_name] = section
    wf_module = create_module_service_spec_from_metadata(
        experiment_dir,
        module_name=service_name,
        module_type="framework_module",
        metadata=metadata_copy,
        module_yaml_path=facts_total_yaml_path,
    )
    compose_svc = wf_module.generate_compose_service()
    compose_svc["depends_on"] = {
        mod: {"condition": "service_completed_successfully"} for mod in wf.module_names
    }
    return compose_svc


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


def _parse_experiment(metadata: Dict[str, Any]) -> _ExperimentPlan:
    """Phase 1 of generating compose:
    Validate metadata and build a typed experiment plan.

    Ths fn is only data transformation, there should be no filesystem I/O beyond module YAML loading.
    """

    # This should raise an error if user has not completed necessary fields in experiment-config.yaml
    check_metadata_has_required_fields(
        metadata_obj=metadata, required_fields=_REQUIRED_FIELDS
    )

    # Get the list of modules included in experiment from manifest in exp config
    _manifest_module_names = _extract_all_module_names_from_manifest(metadata)

    # Use list of modules to load schema for each module
    _schemas = [load_module_schema_by_name(m) for m in _manifest_module_names]

    # Get keys for top level params and fingerprint params from each module in experiment
    _top_level_keys = set(collect_metadata_param_keys(_schemas, "top_level"))
    _fp_keys = set(collect_metadata_param_keys(_schemas, "fingerprint_params"))

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
    experiment_dir: Path,
    registry: ModuleRegistry,
) -> _ModuleSpecs:
    """Phase 2: Create a ModuleServiceSpec for each module in the experiment.

    All filesystem I/O for module YAML loading is isolated here.
    """
    temperature_module: Optional[ModuleServiceSpec] = None
    sealevel_modules: Dict[str, ModuleServiceSpec] = {}
    framework_modules: Dict[str, ModuleServiceSpec] = {}
    esl_modules: Dict[str, ModuleServiceSpec] = {}

    if plan.temperature_module_name.upper() != "NONE":
        temperature_module = create_module_service_spec_from_metadata(
            experiment_dir,
            module_name=plan.temperature_module_name,
            module_type="temperature_module",
            metadata=metadata,
        )
        _log_success("Created %s module", plan.temperature_module_name)
    else:
        logger.info("No temperature module specified (NONE)")
        schemas = _load_schemas(
            sealevel_modules=plan.sealevel_module_names, registry=registry
        )
        _validate_climate_file_inputs(
            metadata=metadata, sealevel_modules=sealevel_modules, schemas=schemas
        )

    for module_name in plan.sealevel_module_names:
        sealevel_modules[module_name] = create_module_service_spec_from_metadata(
            experiment_dir,
            module_name=module_name,
            module_type="sealevel_module",
            metadata=metadata,
        )
        _log_success("Created %s module", module_name)

    for module_name in plan.framework_module_names:
        if _module_is_per_workflow(module_name) and plan.workflows:
            continue
        framework_modules[module_name] = create_module_service_spec_from_metadata(
            experiment_dir,
            module_name=module_name,
            module_type="framework_module",
            metadata=metadata,
        )
        _log_success("Created %s module", module_name)

    for module_name in plan.esl_module_names:
        esl_modules[module_name] = create_module_service_spec_from_metadata(
            experiment_dir,
            module_name=module_name,
            module_type="extreme_sealevel_module",
            metadata=metadata,
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
    registry: ModuleRegistry,
) -> Dict[str, Any]:
    """Build one ESL compose service per workflow, keyed by service name."""
    services: Dict[str, Any] = {}
    if not esl_module_names:
        return services
    if projection_scale == "global":
        logger.info("Skipping per-workflow ESL services (projection_scale=global)")
        return services

    for esl_module_name in esl_module_names:
        try:
            esl_yaml_path = registry.get_module_yaml_path(esl_module_name)
        except FileNotFoundError:
            logger.warning(
                "ESL module YAML not found for '%s', skipping per-workflow ESL",
                esl_module_name,
            )
            continue
        base_section = metadata.get(esl_module_name) or {}
        if not isinstance(base_section, dict):
            base_section = {}
        try:
            exp_paths = get_experiment_paths(metadata, f"{esl_module_name} module")
            module_specific_base = expand_path(
                exp_paths.get("module_specific_input_data"),
                "module-specific-input-data",
            )
        except (KeyError, TypeError):
            module_specific_base = ""
        for _wf_name, wf in workflows.items():
            service_name = f"{esl_module_name}-{wf.name}"
            base_inputs = dict(base_section.get("inputs") or {})
            base_inputs["total_localsl_file"] = wf.total_localsl_path_under_output
            gesla_val = base_inputs.get("gesla_dir")
            if not gesla_val or (
                isinstance(gesla_val, dict) and gesla_val.get("value") in (None, "")
            ):
                if module_specific_base:
                    base_inputs["gesla_dir"] = (
                        f"{module_specific_base}/{esl_module_name}/gesla_data"
                    )
            base_outputs = base_section.get("outputs") or {}
            synthetic_section = {
                **base_section,
                "inputs": base_inputs,
                "outputs": {**base_outputs, "output-dir": "."},
            }
            metadata_copy = dict(metadata)
            metadata_copy[service_name] = synthetic_section
            esl_module = create_module_service_spec_from_metadata(
                experiment_dir,
                module_name=service_name,
                module_type="extreme_sealevel_module",
                metadata=metadata_copy,
                module_yaml_path=esl_yaml_path,
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


def _build_compose_services(
    specs: _ModuleSpecs,
    plan: _ExperimentPlan,
    metadata: Dict[str, Any],
    experiment_dir: Path,
    registry: ModuleRegistry,
) -> Dict[str, Any]:
    """Phase 3: Render ModuleServiceSpecs into Docker Compose service dicts."""
    services: Dict[str, Any] = {}

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

    if plan.workflows:
        per_workflow_fw = [
            m
            for m in plan.framework_module_names
            if _module_is_per_workflow(module_name=m, registry=registry)
        ]
        facts_total_name = per_workflow_fw[0] if per_workflow_fw else "facts-total"
        facts_total_yaml_path = registry.get_module_yaml_path(facts_total_name)
        with open(facts_total_yaml_path, "r") as f:
            facts_total_config = yaml.safe_load(f) or {}
        facts_total_image = facts_total_config.get(
            "container_image", "ghcr.io/fact-sealevel/facts-total:v0.1.2"
        )

        wf_schemas: Dict[str, ModuleSchema] = {}
        for wf in plan.workflows.values():
            for mod_name in wf.module_names:
                if mod_name not in wf_schemas:
                    try:
                        wf_schemas[mod_name] = load_module_schema_by_name(mod_name)
                    except FileNotFoundError:
                        pass

        for wf_name, wf in plan.workflows.items():
            for output_type in facts_total_config.get(
                "output_types", ["global", "local"]
            ):
                if (
                    output_type == "local"
                    and plan.experiment.projection_scale == "global"
                ):
                    logger.info(
                        "Skipping local facts-total for %s (projection_scale=global)",
                        wf_name,
                    )
                    continue
                section = _build_facts_total_section_for_workflow(
                    wf, facts_total_image, output_type
                )
                if output_type == "global":
                    _populate_section_with_global_outputs(
                        section, metadata, wf, wf_schemas
                    )
                else:
                    _populate_section_with_local_outputs(
                        section, metadata, wf, wf_schemas
                    )
                service_name = wf.facts_total_service_name_for_type(output_type)
                compose_svc = _create_facts_total_compose_service(
                    section,
                    service_name,
                    wf,
                    metadata,
                    experiment_dir,
                    facts_total_yaml_path,
                )
                services[service_name] = compose_svc
                _log_success("Created %s workflow service", service_name)

        services.update(
            _create_esl_workflow_services(
                plan.esl_module_names,
                plan.workflows,
                metadata,
                experiment_dir,
                plan.experiment.projection_scale,
                registry=registry,
            )
        )

    if not plan.workflows and plan.experiment.projection_scale != "global":
        for _esl_name, esl_module in specs.esl_modules.items():
            service_name = esl_module.module_name
            services[service_name] = esl_module.generate_compose_service()
            _log_success("Created %s module", service_name)

    return services


def generate_compose(
    metadata: Dict[str, Any], experiment_dir: Path, registry: ModuleRegistry
) -> Dict[str, Any]:
    """
    Generate Docker Compose dict from already-loaded experiment metadata.

    Use this when metadata is already loaded (e.g. from a notebook or test).
    For path-based callers, use generate_compose_from_path().

    Args:
        metadata: Loaded experiment-config.yaml as a dict
        experiment_dir: Path to the experiment directory

    Returns:
        Complete Docker Compose file dictionary
    """
    plan = _parse_experiment(metadata)
    specs = _build_module_specs(plan, metadata, experiment_dir, registry=registry)
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
        specs, plan, metadata, experiment_dir, registry=registry
    )
    return {"services": services}


def generate_compose_from_path(
    metadata_path: Path, registry: ModuleRegistry
) -> Dict[str, Any]:
    """
    Generate Docker Compose dict from a path to experiment-config.yaml.

    Handles I/O setup then delegates to generate_compose().
    For callers with metadata already loaded, use generate_compose() directly.

    Args:
        metadata_path: Path to experiment-config.yaml

    Returns:
        Complete Docker Compose file dictionary
    """
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"When trying to read experiment-metadata file to generate corresponding "
            f"compose file, metadata file not found: {metadata_path}"
        )

    metadata = load_experiment_metadata(metadata_path)
    experiment_dir = metadata_path.parent
    return generate_compose(metadata, experiment_dir, registry=registry)
