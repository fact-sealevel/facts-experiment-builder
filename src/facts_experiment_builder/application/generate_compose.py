#!/usr/bin/env python3
"""Generate Docker Compose file from experiment config."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from facts_experiment_builder.application.execution_plan import (
    _ModuleSpecs,
    _collect_workflow_output_paths_by_type,  # noqa: F401 — re-exported for tests
    build_experiment_execution_plan,
)
from facts_experiment_builder.application.storage import (
    ExperimentRepository,
)
from facts_experiment_builder.core.experiment.experiment_plan import (
    _ExperimentPlan,
    _make_experiment_plan,
)
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
)
from facts_experiment_builder.application.module_service_spec_factory import (
    build_module_service_spec,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
    resolve_experiment_data_paths,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
)
from facts_experiment_builder.io.paths import ExperimentPaths

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
class PrepareComposeOutput:
    compose_dict: dict
    compose_path: Path


def _log_success(msg: str, *args: object) -> None:
    logger.log(_SUCCESS, msg, *args)


def _extract_all_module_names_from_manifest(metadata: dict[str, Any]) -> list[str]:
    """Extract a flat list of all module names from the experiment manifest keys."""
    names: list[str] = []
    climate_mod = metadata.get("climate_module")
    if climate_mod and str(climate_mod).upper() != "NONE":
        names.append(str(climate_mod))
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
    metadata: dict[str, Any],
    sealevel_modules: list[str],
    schemas: dict[str, ModuleSchema],
) -> None:
    """Validate that sealevel modules have climate file inputs when no climate module is
    specified.

    Pure logic — accepts pre-loaded schemas. Raises ValueError listing any modules that
    require a climate file but have no value provided in metadata.
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
            f"No climate module specified, but the following sealevel modules are missing "
            f"climate file inputs: {', '.join(missing_climate_files)}. "
            f"Please provide the climate file input (e.g. 'climate_data_file' or the module-specific "
            f"input key) in the inputs section for each sealevel module."
        )


def check_metadata_has_required_fields(metadata_obj, required_fields):
    """This function accepts a list of required fields and a metadata object and subsets
    the metadata to required fields."""
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


def check_module_schemas_present(
    metadata: dict[str, Any],
    required_module_names: Iterable[str],
) -> None:
    """Raise an informative error if the experiment-config.yaml file associated with
    provided experiment_name does not contain module schemas section, or is missing
    schema data for a module."""
    module_schemas = metadata.get("module_schemas")
    if not isinstance(module_schemas, dict) or not module_schemas:
        raise ValueError(
            "This experiment's experiment-config.yaml file does not contain a 'module_schemas' section. "
            "It may be that the file was created with an older version of FEB that included a different `setup-experiment` command."
            "`generate-compose` now reads module schema information directly from experiment-config.yaml instead of the local module registry."
            "Please ensure you are using the latest version of FEB and re-run `setup-experiment`."
        )
    missing = sorted(set(required_module_names) - set(module_schemas))
    if missing:
        raise ValueError(
            f"This experiment's experiment-config.yaml is missing module schema "
            f"information for: {', '.join(missing)}. Please re-run `setup-experiment` "
            f"to regenerate a compatible experiment-config.yaml."
        )


def _build_module_specs(
    plan: _ExperimentPlan,
    metadata: dict[str, Any],
    schemas: dict,
    known_module_names: list,
    data_paths: ExperimentDataPaths,
) -> _ModuleSpecs:
    """Phase 2: Create a ModuleServiceSpec for each module in the experiment.

    All filesystem I/O for module YAML loading is isolated here.
    """
    climate_module: ModuleServiceSpec | None = None
    sealevel_modules: dict[str, ModuleServiceSpec] = {}
    framework_modules: dict[str, ModuleServiceSpec] = {}
    esl_modules: dict[str, ModuleServiceSpec] = {}

    climate_module_definition = schemas[plan.climate_module_name]
    if plan.climate_module_name.upper() != "NONE":
        climate_module_name = plan.climate_module_name
        climate_module = build_module_service_spec(
            metadata=metadata,
            module_name=climate_module_name,
            known_module_names=known_module_names,
            module_definition=climate_module_definition,
            data_paths=data_paths,
        )
        _log_success("Created %s module", plan.climate_module_name)
    else:
        logger.info("No climate module specified (NONE)")

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
            data_paths=data_paths,
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
            data_paths=data_paths,
        )

        _log_success("Created %s module", module_name)

    for module_name in plan.esl_module_names:
        schema = schemas[module_name]
        esl_modules[module_name] = build_module_service_spec(
            metadata=metadata,
            module_name=module_name,
            known_module_names=known_module_names,
            module_definition=schema,
            data_paths=data_paths,
        )

        _log_success("Created %s module", module_name)

    # Make _ModuleSpecs obj
    # This is what's returned by _build_module_specs
    # and used by _build_compose_servies()
    specs = _ModuleSpecs(
        climate_module=climate_module,
        sealevel_modules=sealevel_modules,
        framework_modules=framework_modules,
        esl_modules=esl_modules,
    )

    if not any(
        [
            specs.climate_module,
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


def _build_compose_services(
    specs: _ModuleSpecs,
    plan: _ExperimentPlan,
    metadata: dict[str, Any],
    experiment_dir: Path,
    schemas: dict[str, ModuleSchema],
    data_paths: ExperimentDataPaths,
) -> dict[str, Any]:
    """Phase 3: Render ModuleServiceSpecs into Docker Compose service dicts."""
    execution_plan = build_experiment_execution_plan(
        specs=specs,
        plan=plan,
        metadata=metadata,
        schemas=schemas,
        data_paths=data_paths,
    )
    services: dict[str, Any] = {}

    for service_name, spec in execution_plan.standard_specs.items():
        services[service_name] = spec.generate_compose_service(
            climate_service_name=execution_plan.climate_service_name,
            suppress_output_types=execution_plan.suppress_output_types,
        )

    for service_name, (spec, wf) in execution_plan.facts_total_specs.items():
        compose_svc = spec.generate_compose_service()
        compose_svc["depends_on"] = {
            mod: {"condition": "service_completed_successfully"}
            for mod in wf.module_names
        }
        services[service_name] = compose_svc
        _log_success("Created %s workflow service", service_name)

    for service_name, (spec, depends_on_service) in execution_plan.esl_specs.items():
        compose_svc = spec.generate_compose_service()
        compose_svc["depends_on"] = {
            depends_on_service: {"condition": "service_completed_successfully"}
        }
        services[service_name] = compose_svc
        _log_success("Created %s ESL workflow service", service_name)

    for service_name, spec in execution_plan.standalone_esl_specs.items():
        services[service_name] = spec.generate_compose_service()
        _log_success("Created %s module", service_name)

    return services


def generate_compose(
    experiment_name: str,
    workspace_dir: Path,
    experiment_repo: ExperimentRepository,
    custom_compose_path: Path | None = None,
) -> dict[str, Any]:
    """Generate Docker Compose dict from already-loaded experiment metadata.

    Args:
        metadata: Loaded experiment-config.yaml as a dict
        experiment_dir: Path to the experiment directory

    Returns:
        Complete Docker Compose file dictionary
    """
    # TODO: in future, should probably make a dataclass or similar for experiment metadata dict so that
    # can just access an attr instead of needing fns to get names from manifest etc?

    experiment_name_obj = ExperimentName.parse(raw_name=experiment_name)

    experiment_paths = ExperimentPaths(
        workspace_dir=workspace_dir,
        experiment_name=experiment_name_obj,
    )
    # experiment_paths.custom_compose_path = custom_compose_path

    # handle custom compose, if passed -- is this still necessary?
    compose_path = (
        custom_compose_path.resolve()
        if custom_compose_path is not None
        else experiment_paths.compose_path
    )
    experiment_dir = experiment_paths.config_path.parent

    # Check that paths are valid
    assert experiment_dir.is_dir(), (
        f"Expected 'experiment_dir.is_dir() is True', received: {experiment_dir.is_dir()}."
    )
    config_path = experiment_paths.config_path
    assert config_path.exists(), (
        f"Did not find `experiment-config.yaml` at '{config_path}'. Please ensure correct path/experiment name."
    )

    # log message to send to CLI
    logger.info(
        "Found experiment config file at provided path", extra={"detail": config_path}
    )

    metadata_dict = experiment_repo.get(
        config_path=config_path,
    )

    module_names = _extract_all_module_names_from_manifest(metadata_dict)

    # Check that module_schemas section present
    check_module_schemas_present(metadata_dict, module_names)

    schemas = {
        m_name: ModuleSchema.from_dict(metadata_dict["module_schemas"][m_name])
        for m_name in set(module_names)
    }
    known_module_names = list(schemas.keys())

    # Make experiment plan
    plan = _make_experiment_plan(metadata_dict, schemas)
    data_paths = resolve_experiment_data_paths(metadata_dict)
    specs = _build_module_specs(
        plan=plan,
        metadata=metadata_dict,
        schemas=schemas,
        known_module_names=known_module_names,
        data_paths=data_paths,
    )
    if not any(
        [
            specs.climate_module,
            specs.sealevel_modules,
            specs.framework_modules,
            specs.esl_modules,
        ]
    ):
        return {"services": {}}
    services = _build_compose_services(
        specs,
        plan,
        metadata_dict,
        experiment_dir,
        schemas=schemas,
        data_paths=data_paths,
    )
    output_obj = PrepareComposeOutput(
        compose_dict={"services": services}, compose_path=compose_path
    )
    return output_obj
