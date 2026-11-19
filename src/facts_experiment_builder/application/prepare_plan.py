#!/usr/bin/env python3
"""Plan an experiment's services from its loaded config, independent of the backend.

prepare_execution_plan() is the single planning entry point. generate_run_file() passes
its result to execution_graph.build_execution_graph().
"""

import logging
from collections.abc import Iterable
from typing import Any

from facts_experiment_builder.application.execution_plan import (
    _ExecutionPlan,
    _build_esl_specs_for_workflows,
    _build_facts_total_specs_for_workflows,
)
from facts_experiment_builder.application.module_service_spec_factory import (
    build_module_service_spec,
)
from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.core.experiment.experiment import (
    check_totaling_and_esl_have_workflows,
)
from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
    collect_metadata_param_keys,
)
from facts_experiment_builder.core.workflow import workflows_from_mapping
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SUCCESS = 25  # custom level between INFO (20) and WARNING (30); must match CLI handler


def _log_success(msg: str, *args: object) -> None:
    logger.log(_SUCCESS, msg, *args)


def _validate_climate_file_inputs(
    config: LoadedExperimentConfig,
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

        module_inputs = config.module_sections.get(module_name, {}).get("inputs", {})
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


def _load_module_schemas(config: LoadedExperimentConfig) -> dict[str, ModuleSchema]:
    """Parse the module schemas stored in experiment-config.yaml, one per module.

    Raises ValueError if the config has no module_schemas section or is missing one.
    """
    # Check first, so a config from an older setup-experiment gets an explanation
    # instead of a KeyError from the lookup below.
    check_module_schemas_present(config.module_schemas, config.module_names)
    # set(): a module listed in more than one step only needs parsing once.
    return {
        m: ModuleSchema.from_dict(config.module_schemas[m])
        for m in set(config.module_names)
    }


def _build_standard_specs(
    climate_module: str | None,
    sealevel_modules: list[str],
    config: LoadedExperimentConfig,
    schemas: dict[str, ModuleSchema],
    data_paths: ExperimentDataPaths,
) -> dict[str, ModuleServiceSpec]:
    """Build the climate module's spec, if there is one, and one spec per sea-level
    module, keyed by service name with the climate module first.

    Without a climate module, every climate-dependent sea-level module must have its
    climate file input set; _validate_climate_file_inputs() raises otherwise.
    """
    known_module_names = list(schemas)

    # Every climate and sea-level spec is built the same way, from the module's own
    # section of experiment-config.yaml.
    def build(module_name: str) -> ModuleServiceSpec:
        spec = build_module_service_spec(
            config.module_sections.get(module_name, {}),
            config=config,
            module_name=module_name,
            known_module_names=known_module_names,
            module_definition=schemas[module_name],
            data_paths=data_paths,
        )
        _log_success("Created %s module", module_name)
        return spec

    # Insertion order is run order: the climate module goes in first, so it is the
    # first service in the generated run file.
    specs: dict[str, ModuleServiceSpec] = {}
    if climate_module is not None:
        specs[climate_module] = build(climate_module)
    else:
        logger.info("No climate module specified (NONE)")
        # With no climate module to produce it, each climate-dependent sea-level module
        # must name its climate file in experiment-config.yaml.
        _validate_climate_file_inputs(
            config=config,
            sealevel_modules=sealevel_modules,
            schemas=schemas,
        )

    for module_name in sealevel_modules:
        specs[module_name] = build(module_name)
    return specs


def prepare_execution_plan(
    config: LoadedExperimentConfig,
    data_paths: ExperimentDataPaths,
) -> _ExecutionPlan:
    """Plan every service the experiment runs, independent of the backend.

    data_paths is passed in rather than resolved here so that a caller can relocate the
    output root (Apptainer writes to its own output directory).

    Facts-total and ESL services are built per workflow, from the sea-level modules'
    outputs. If there are no climate or sea-level modules, nothing is built: that is
    allowed only when the experiment supplies step data, and returns an empty plan.
    """
    schemas = _load_module_schemas(config)
    module_schemas = list(schemas.values())
    # Pass the param keys the module schemas declare, so the experiment's params are
    # grouped exactly as the modules define them. Planning itself reads only the steps
    # and projection scale below.
    experiment = FactsExperiment.from_loaded_config(
        config,
        top_level_keys=set(collect_metadata_param_keys(module_schemas, "top_level")),
        fingerprint_keys=set(
            collect_metadata_param_keys(module_schemas, "fingerprint_params")
        ),
    )

    # Which modules run in which step. The step objects have already normalised the
    # manifest: a missing or "NONE" climate module gives module_name None.
    climate_module = experiment.climate_step.module_name
    sealevel_modules = experiment.sealevel_step.module_names
    framework_modules = (
        [experiment.totaling_step.module_name]
        if experiment.totaling_step.is_present
        else []
    )
    esl_modules = (
        [experiment.extreme_sealevel_step.module_name]
        if experiment.extreme_sealevel_step.is_present
        else []
    )
    workflows = workflows_from_mapping(config.workflows)
    workflow_names = list(workflows)
    # Fail before building any spec if facts-total or ESL could never get their inputs.
    check_totaling_and_esl_have_workflows(
        sealevel_module_names=sealevel_modules,
        framework_module_names=framework_modules,
        esl_module_names=esl_modules,
        workflows=workflows,
    )
    # A global-only experiment produces no local outputs, so no service writes them.
    suppress_output_types: set[str] = (
        {"local"} if experiment.projection_scale == "global" else set()
    )

    # Climate and sea-level specs come first: facts-total and ESL are built from the
    # sea-level modules' outputs.
    standard_specs = _build_standard_specs(
        climate_module, sealevel_modules, config, schemas, data_paths
    )
    if not standard_specs:
        # Nothing to run is only valid when every step's data was supplied up front.
        has_step_data = bool(
            config.supplied_totaled_sealevel_step_data
            or config.experiment_specific_input_data
        )
        if not has_step_data:
            raise ValueError(
                "No modules could be created from metadata. "
                "Please ensure at least one module is specified and has valid configuration."
            )
        logger.info(
            "All experiment steps use pre-existing data. No Docker services to generate."
        )
        return _ExecutionPlan(
            standard_specs={},
            facts_total_specs={},
            esl_specs={},
            climate_service_name=None,
            suppress_output_types=suppress_output_types,
            workflow_names=workflow_names,
        )

    # Facts-total and ESL run once per workflow, so without workflows there are none.
    # check_totaling_and_esl_have_workflows() above already rejected a totaling step
    # with no workflows.
    facts_total_specs = (
        _build_facts_total_specs_for_workflows(
            framework_module_names=framework_modules,
            workflows=workflows,
            projection_scale=experiment.projection_scale,
            config=config,
            schemas=schemas,
            data_paths=data_paths,
        )
        if workflows
        else {}
    )
    esl_specs = (
        _build_esl_specs_for_workflows(
            esl_module_names=esl_modules,
            workflows=workflows,
            config=config,
            projection_scale=experiment.projection_scale,
            schemas=schemas,
            data_paths=data_paths,
        )
        if workflows
        else {}
    )
    return _ExecutionPlan(
        standard_specs=standard_specs,
        facts_total_specs=facts_total_specs,
        esl_specs=esl_specs,
        # A named climate module always gets a spec above, so its name is the service.
        climate_service_name=climate_module,
        suppress_output_types=suppress_output_types,
        workflow_names=workflow_names,
    )
