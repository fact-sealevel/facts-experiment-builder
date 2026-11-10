"""Shared pipeline from loaded experiment config to a format-agnostic _ExecutionPlan.

Both generate-compose and generate-apptainer call prepare_execution_plan() and then
render the result in their own format.
"""

import logging
from collections.abc import Iterable
from typing import Any

from facts_experiment_builder.application.execution_plan import (
    _ExecutionPlan,
    _ModuleSpecs,
    build_experiment_execution_plan,
)
from facts_experiment_builder.application.log_levels import SUCCESS
from facts_experiment_builder.application.module_service_spec_factory import (
    build_module_service_spec,
)
from facts_experiment_builder.core.experiment.experiment_plan import (
    _ExperimentPlan,
    _make_experiment_plan,
)
from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _log_success(msg: str, *args: object) -> None:
    logger.log(SUCCESS, msg, *args)


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


def check_module_schemas_present(
    module_schemas: dict[str, Any] | None,
    required_module_names: Iterable[str],
) -> None:
    """Raise an informative error if the experiment-config.yaml file associated with
    provided experiment_name does not contain module schemas section, or is missing
    schema data for a module."""
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
    """Create a ModuleServiceSpec for each module in the experiment."""
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

    specs = _ModuleSpecs(
        climate_module=climate_module,
        sealevel_modules=sealevel_modules,
        framework_modules=framework_modules,
        esl_modules=esl_modules,
    )

    if specs.is_empty:
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


def prepare_execution_plan(
    config: LoadedExperimentConfig,
    data_paths: ExperimentDataPaths,
) -> tuple[_ExperimentPlan, _ExecutionPlan]:
    """Turn a loaded experiment config into a format-agnostic _ExecutionPlan.

    data_paths is passed in rather than resolved here so that a caller can relocate the
    output root (Apptainer writes to its own output directory). Returns the
    _ExperimentPlan as well, since renderers may need its workflows.

    If no module services can be created (every step uses pre-existing data), returns an
    empty _ExecutionPlan.
    """
    module_names = config.module_names
    check_module_schemas_present(config.module_schemas, module_names)

    schemas = {
        m: ModuleSchema.from_dict(config.module_schemas[m]) for m in set(module_names)
    }
    # Functions below still take the metadata dict.
    metadata = config.raw
    known_module_names = list(schemas.keys())

    plan = _make_experiment_plan(metadata, schemas)
    specs = _build_module_specs(
        plan=plan,
        metadata=metadata,
        schemas=schemas,
        known_module_names=known_module_names,
        data_paths=data_paths,
    )
    if specs.is_empty:
        return plan, _ExecutionPlan(
            standard_specs={},
            facts_total_specs={},
            esl_specs={},
            climate_service_name=None,
            suppress_output_types=plan.suppress_output_types,
        )

    execution_plan = build_experiment_execution_plan(
        specs=specs,
        plan=plan,
        metadata=metadata,
        schemas=schemas,
        data_paths=data_paths,
    )
    return plan, execution_plan
