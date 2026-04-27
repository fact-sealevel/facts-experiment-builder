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
from pathlib import Path
from typing import Dict, Any, List

from facts_experiment_builder.adapters.module_adapter import (
    create_module_service_spec_from_metadata,
)
from facts_experiment_builder.adapters.adapter_utils import get_experiment_paths
from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.core.workflow.workflow import (
    Workflow,
    workflows_from_metadata,
)
from facts_experiment_builder.infra.path_manager import find_module_yaml_path
from facts_experiment_builder.infra.path_utils import expand_path
from facts_experiment_builder.infra.experiment_loader import load_experiment_metadata
from facts_experiment_builder.infra.module_loader import (
    load_facts_module_from_yaml,
    load_facts_module_by_name,
)
from facts_experiment_builder.core.module.module_schema import (
    collect_metadata_param_keys,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


def _module_requires_climate_file(module_name: str) -> bool:
    """
    Check if a module requires a climate file by loading its module YAML configuration.

    Args:
        module_name: Name of the module (e.g., 'bamber19-icesheets')

    Returns:
        True if climate_file_required is True in module YAML, False otherwise
    """

    # Get path
    module_yaml_path = find_module_yaml_path(module_name)
    # Load module yaml
    module_yaml = load_facts_module_from_yaml(yaml_path=module_yaml_path)
    # Return uses climate file attr
    return module_yaml.uses_climate_file


def _validate_climate_file_inputs(
    metadata: Dict[str, Any], sealevel_modules: List[str], experiment_dir: Path
) -> None:
    """
    Validate that sealevel modules have climate file inputs when no temperature module is specified.
    Only validates modules that have climate_file_required=True in their module YAML.

    Args:
        metadata: Experiment metadata dictionary
        sealevel_modules: List of sealevel module names
        experiment_dir: Path to experiment directory (used to find module YAML files)

    Raises:
        ValueError: If any sealevel module that requires climate files is missing climate file input
    """
    missing_climate_files = []

    for module_name in sealevel_modules:
        module_yaml_path = find_module_yaml_path(module_name)
        module_schema = load_facts_module_from_yaml(yaml_path=module_yaml_path)

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
    *,
    container_prefix: str = "/mnt/total_out",
) -> List[str]:
    """
    Collect container paths for workflow module outputs that match the given output_type.

    For each module in the workflow, reads metadata[mod].outputs; each value can be
    a string path or a dict with "value" and "output_type". Missing output_type
    is treated as "local" for backward compatibility.
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
        for v in outputs.values():
            if isinstance(v, dict) and "value" in v:
                p = v.get("value") or ""
                ot = v.get("output_type", "")
            elif isinstance(v, str):
                p = v
                ot = "local"
            else:
                continue
            if p and isinstance(p, str) and ot == output_type:
                paths.append(f"{prefix}/{p.strip()}")
    return paths


def _module_is_per_workflow(module_name: str) -> bool:
    """Return True if the module YAML declares per_workflow: true."""
    try:
        module_yaml_path = find_module_yaml_path(module_name)
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
) -> None:
    """Extend section["inputs"]["item"] with container paths for outputs with output_type "global"."""
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "global")
    section["inputs"]["item"].extend(paths)


def _populate_section_with_local_outputs(
    section: Dict[str, Any],
    metadata: Dict[str, Any],
    wf: Workflow,
) -> None:
    """Extend section["inputs"]["item"] with container paths for outputs with output_type "local"."""
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "local")
    section["inputs"]["item"].extend(paths)


def _create_facts_total_compose_service(
    section: Dict[str, Any],
    service_name: str,
    wf: Workflow,
    metadata: Dict[str, Any],
    metadata_path: Path,
    facts_total_yaml_path: Path,
) -> Dict[str, Any]:
    """Build the compose service dict for a facts-total workflow from its synthetic section."""
    metadata_copy = dict(metadata)
    metadata_copy[service_name] = section
    wf_module = create_module_service_spec_from_metadata(
        metadata_path,
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


def generate_compose_from_metadata(metadata_path: Path) -> Dict[str, Any]:
    """
    Generate Docker Compose file from experiment metadata.

    This is the main orchestration function that:
    1. Loads metadata (UI layer)
    2. Parses manifest to determine which modules to include
    3. Uses parsers (Adapter layer) to create domain objects (modules)
    4. Generates docker compose services (Engine/Infrastructure layer)

    Args:
        metadata_path: Path to experiment-config.yaml

    Returns:
        Complete Docker Compose file dictionary
    """
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"When trying to read experiment-metadata file to generate corresponding compose file, metadata file not found: {metadata_path}"
        )

    # Step 1: Load metadata (UI layer)
    metadata = load_experiment_metadata(metadata_path)
    # Check that required fields in experient-config have been completed
    # TODO do this better in future
    required_fields = [
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
    # subset metadata to required fields
    required_fields_meta = {k: v for k, v in metadata.items() if k in required_fields}
    # raise error if any are missing a value
    for k, v in required_fields_meta.items():
        if v is None:
            raise ValueError(
                f"A value for {k} is required but none was found. Check that all required fields in this experiment's experiment-config.yml file have been completed."
            )
    experiment_dir = metadata_path.parent

    # Step 2: Build FactsExperiment — derive key sets from module schemas
    _manifest_module_names = _extract_all_module_names_from_manifest(metadata)
    _schemas = [load_facts_module_by_name(m) for m in _manifest_module_names]
    _top_level_keys = set(collect_metadata_param_keys(_schemas, "top_level"))
    _fp_keys = set(collect_metadata_param_keys(_schemas, "fingerprint_params"))
    experiment = FactsExperiment.from_metadata_dict(
        metadata,
        top_level_keys=_top_level_keys,
        fingerprint_keys=_fp_keys,
    )

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

    # Step 3: Create ModuleServiceSpec instances using parsers (Adapter layer -> Domain layer)
    # modules = []
    modules = {
        "temperature_module": None,
        "sealevel_modules": {},
        "framework_modules": {},
        "esl_modules": {},
    }

    # Create temperature module if specified (and not "NONE")
    if temperature_module_name and temperature_module_name.upper() != "NONE":
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=temperature_module_name,
                module_type="temperature_module",
                metadata=metadata,
            )
            # modules.append(module)
            modules["temperature_module"] = module
            print(f"✓ Created {temperature_module_name} module")
        except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
            print(
                f"⚠ Warning: Failed to create temp module '{temperature_module_name}': {e}"
            )
    elif temperature_module_name and temperature_module_name.upper() == "NONE":
        # No temperature module - validate that sealevel modules have climate file inputs
        # Only validate modules that have climate_file_required=True
        print("ℹ No temperature module specified (NONE)")
        _validate_climate_file_inputs(metadata, sealevel_module_names, experiment_dir)

    # Create sea level modules if specified
    for module_name in sealevel_module_names:
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=module_name,
                module_type="sealevel_module",
                metadata=metadata,
            )
            # modules.append(module)
            modules["sealevel_modules"][module_name] = module
            print(f"✓ Created {module_name} module")
        except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
            print(f"⚠ Warning: Failed to create sealevel module '{module_name}': {e}")

    # Create framework modules if specified (skip per-workflow modules when workflows exist; we add per-workflow services below)
    workflows = workflows_from_metadata(metadata)
    for module_name in framework_module_names:
        if _module_is_per_workflow(module_name) and workflows:
            continue  # per-workflow modules are added once per workflow below
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=module_name,
                module_type="framework_module",
                metadata=metadata,
            )
            modules["framework_modules"][module_name] = module
            print(f"✓ Created {module_name} module")
        except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
            print(f"⚠ Warning: Failed to create framework module '{module_name}': {e}")

    # Create ESL modules if specified
    for module_name in esl_module_names:
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=module_name,
                module_type="extreme_sealevel_module",
                metadata=metadata,
            )
            # modules.append(module)
            modules["esl_modules"][module_name] = module
            print(f"✓ Created {module_name} module")
        except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
            print(f"⚠ Warning: Failed to create ESL module '{module_name}': {e}")

    if (
        not modules["temperature_module"]
        and not modules["sealevel_modules"]
        and not modules["framework_modules"]
        and not modules["esl_modules"]
    ):
        has_step_data = bool(
            metadata.get("supplied-totaled-sealevel-step-data")
            or metadata.get("experiment-specific-input-data")
        )
        if has_step_data:
            print(
                "ℹ All experiment steps use pre-existing data. No Docker services to generate."
            )
            return {"services": {}}
        raise ValueError(
            "No modules could be created from metadata. "
            "Please ensure at least one module is specified and has valid configuration."
        )

    # Step 4: Generate Docker Compose services (Engine/Infrastructure layer)
    services = {}

    # Add temperature module service if present
    temperature_module = modules["temperature_module"]
    temperature_module_name = (
        temperature_module.module_name if temperature_module else None
    )

    if temperature_module:
        services[temperature_module_name] = (
            temperature_module.generate_compose_service()
        )

    # Add sealevel modules directly to services (flat structure for Docker Compose)
    for module_name, module in modules["sealevel_modules"].items():
        service_name = module.module_name
        compose_service = module.generate_compose_service(
            temperature_service_name=temperature_module_name
        )
        services[service_name] = compose_service

    # Add one facts-total service per workflow (after sealevel services)
    if workflows:
        per_workflow_fw = [
            m for m in framework_module_names if _module_is_per_workflow(m)
        ]
        facts_total_name = per_workflow_fw[0] if per_workflow_fw else "facts-total"
        facts_total_yaml_path = find_module_yaml_path(facts_total_name)
        with open(facts_total_yaml_path, "r") as f:
            facts_total_config = yaml.safe_load(f) or {}
        facts_total_image = facts_total_config.get(
            "container_image", "ghcr.io/fact-sealevel/facts-total:v0.1.2"
        )
        for wf_name, wf in workflows.items():
            for output_type in facts_total_config.get(
                "output_types", ["global", "local"]
            ):
                section = _build_facts_total_section_for_workflow(
                    wf, facts_total_image, output_type
                )
                if output_type == "global":
                    _populate_section_with_global_outputs(section, metadata, wf)
                else:
                    _populate_section_with_local_outputs(section, metadata, wf)
                service_name = wf.facts_total_service_name_for_type(output_type)
                try:
                    compose_svc = _create_facts_total_compose_service(
                        section,
                        service_name,
                        wf,
                        metadata,
                        metadata_path,
                        facts_total_yaml_path,
                    )
                    services[service_name] = compose_svc
                    print(f"✓ Created {service_name} workflow service")
                except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
                    print(
                        f"⚠ Warning: Failed to create workflow service '{service_name}': {e}"
                    )

        # One ESL service per workflow when both workflows and esl_modules are specified
        if esl_module_names:
            for esl_module_name in esl_module_names:
                try:
                    esl_yaml_path = find_module_yaml_path(esl_module_name)
                except FileNotFoundError:
                    print(
                        f"⚠ Warning: ESL module YAML not found for '{esl_module_name}', skipping per-workflow ESL"
                    )
                    continue
                base_section = metadata.get(esl_module_name) or {}
                if not isinstance(base_section, dict):
                    base_section = {}
                # Resolve module-specific input base so we can set gesla_dir when it's a placeholder
                try:
                    exp_paths = get_experiment_paths(
                        metadata, f"{esl_module_name} module"
                    )
                    module_specific_base = expand_path(
                        exp_paths.get("module_specific_input_data"),
                        "module-specific-input-data",
                    )
                except (KeyError, TypeError):
                    module_specific_base = ""
                for wf_name, wf in workflows.items():
                    service_name = f"{esl_module_name}-{wf.name}"
                    base_inputs = dict(base_section.get("inputs") or {})
                    base_inputs["total_localsl_file"] = (
                        wf.total_localsl_path_under_output
                    )
                    # Ensure gesla_dir is a valid path so --gesla-dir appears in the compose command
                    gesla_val = base_inputs.get("gesla_dir")
                    if not gesla_val or (
                        isinstance(gesla_val, dict)
                        and gesla_val.get("value") in (None, "")
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
                    try:
                        esl_module = create_module_service_spec_from_metadata(
                            metadata_path,
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
                        print(f"✓ Created {service_name} ESL workflow service")
                    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
                        print(
                            f"⚠ Warning: Failed to create ESL workflow service '{service_name}': {e}"
                        )

    # When there are no workflows, add a single ESL service per ESL module
    if not workflows:
        for _esl_name, esl_module in modules["esl_modules"].items():
            service_name = esl_module.module_name
            services[service_name] = esl_module.generate_compose_service()
            print(f"✓ Created {service_name} module")

    # Step 5: Build complete Docker Compose file as dict
    compose_dict = {"services": services}

    return compose_dict
