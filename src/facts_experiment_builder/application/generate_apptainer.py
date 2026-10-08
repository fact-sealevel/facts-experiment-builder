#!/usr/bin/env python3
"""Generate Apptainer bash script from experiment config."""

import dataclasses
import logging
from dataclasses import dataclass
from pathlib import Path

from facts_experiment_builder.application.execution_plan import (
    _ExecutionPlan,
    build_experiment_execution_plan,
)
from facts_experiment_builder.application.generate_compose import (
    _build_module_specs,
    _extract_all_module_names_from_manifest,
    check_module_schemas_present,
)
from facts_experiment_builder.application.storage import ExperimentRepository
from facts_experiment_builder.core.experiment.experiment_plan import (
    _make_experiment_plan,
)
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.core.module.apptainer_service_spec import (
    ApptainerServiceSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
    resolve_experiment_data_paths,
)
from facts_experiment_builder.core.module.module_service_spec import ModuleServiceSpec
from facts_experiment_builder.io.paths import ExperimentPaths
from facts_experiment_builder.io.write_apptainer import (
    render_apptainer_script,
    write_apptainer_script,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SUCCESS = 25


@dataclass(frozen=True)
class _ApptainerStages:
    """ApptainerServiceSpec objects grouped by execution stage."""

    stage1: list[ApptainerServiceSpec]  # climate + non-climate-dependent sealevel
    stage2: list[ApptainerServiceSpec]  # sealevel where uses_climate_file=True
    stage3: list[
        ApptainerServiceSpec
    ]  # facts-total × workflow × output_type (parallel)
    stage4: list[ApptainerServiceSpec]  # ESL × workflow (sequential)
    all_specs: list[ApptainerServiceSpec]  # stage1+2+3+4; ordered for pull + mkdir


@dataclass(frozen=True)
class GenerateApptainerOutput:
    script_path: Path


def _log_success(msg: str, *args: object) -> None:
    logger.log(_SUCCESS, msg, *args)


def _get_climate_wait_files(
    spec: ModuleServiceSpec,
    climate: ApptainerServiceSpec,
) -> list[str]:
    """Return host paths `spec` must wait for from the climate service's outputs.

    The climate outputs `spec` needs are named by its inputs' climate_step_output; their
    host paths come from the climate service's host_outputs.
    """
    needed = {
        inp.climate_step_output
        for inp in spec.module_definition.arguments.inputs
        if inp.climate_step_output
    }
    return [path for name, path in climate.host_outputs.items() if name in needed]


def _build_apptainer_stages(execution_plan: _ExecutionPlan) -> _ApptainerStages:
    """Map _ExecutionPlan fields to Apptainer execution stages.

    ModuleServiceSpec is only read here to choose stages (uses_climate_file) and which
    climate outputs a module needs; everything else comes from ApptainerServiceSpec.
    """
    suppress = execution_plan.suppress_output_types

    # Build the climate service first so Stage 2 can wait on its outputs.
    climate_name = execution_plan.climate_service_name
    climate_module_spec = (
        execution_plan.standard_specs.get(climate_name) if climate_name else None
    )
    climate: ApptainerServiceSpec | None = (
        climate_module_spec.generate_apptainer_service(suppress_output_types=suppress)
        if climate_module_spec
        else None
    )

    stage1: list[ApptainerServiceSpec] = []
    stage2: list[ApptainerServiceSpec] = []
    for service_name, spec in execution_plan.standard_specs.items():
        if climate is not None and service_name == climate_name:
            stage1.append(climate)
        elif not spec.module_definition.uses_climate_file:
            stage1.append(
                spec.generate_apptainer_service(suppress_output_types=suppress)
            )
        else:
            wait_files = _get_climate_wait_files(spec, climate) if climate else []
            stage2.append(
                spec.generate_apptainer_service(
                    wait_for_files=wait_files, suppress_output_types=suppress
                )
            )

    stage3: list[ApptainerServiceSpec] = []
    for service_name, (spec, _wf) in execution_plan.facts_total_specs.items():
        pid_var = f"PID_{service_name.upper().replace('-', '_')}"
        stage3.append(
            spec.generate_apptainer_service(
                run_in_background=True,
                pid_var=pid_var,
            )
        )

    # Stage 4 runs after Stage 3 has finished, so per-workflow ESL services see their
    # totaled inputs. ESL services for experiments without workflows have no totaling
    # dependency and run here too.
    stage4: list[ApptainerServiceSpec] = []
    for _service_name, (spec, _depends_on) in execution_plan.esl_specs.items():
        stage4.append(spec.generate_apptainer_service())
    for spec in execution_plan.standalone_esl_specs.values():
        stage4.append(spec.generate_apptainer_service())

    all_specs = stage1 + stage2 + stage3 + stage4
    return _ApptainerStages(
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
        all_specs=all_specs,
    )


def _with_apptainer_output_root(
    data_paths: ExperimentDataPaths, experiment_paths: ExperimentPaths
) -> ExperimentDataPaths:
    """Return data_paths with the output root replaced by the Apptainer output dir.

    Apptainer outputs go to ExperimentPaths.apptainer_output_dir instead of the config's
    output-data-location (used by Compose), so both can run for the same experiment.
    Every derived output path (binds, mkdir dirs, wait files, OUTPUT_DIR) follows from
    this one value.
    """
    return dataclasses.replace(
        data_paths,
        output_data_location=str(experiment_paths.apptainer_output_dir),
    )


def _compute_mkdir_dirs(stages: _ApptainerStages) -> list[str]:
    """Collect unique service output directories in stage order."""
    return list(dict.fromkeys(spec.output_dir for spec in stages.all_specs))


def generate_apptainer(
    experiment_name: str,
    workspace_dir: Path,
    experiment_repo: ExperimentRepository,
    custom_script_path: Path | None = None,
) -> GenerateApptainerOutput:
    """Generate Apptainer bash script from experiment metadata.

    Args:
        experiment_name: Name of the experiment (may include parent dir prefix).
        workspace_dir: Absolute path to the workspace root directory.
        experiment_repo: Repository for loading experiment-config.yaml.
        custom_script_path: Override output path; defaults to
            experiment_dir/experiment-apptainer.sh.

    Returns:
        GenerateApptainerOutput with the path of the written script.
    """
    experiment_name_obj = ExperimentName.parse(raw_name=experiment_name)
    experiment_paths = ExperimentPaths(
        workspace_dir=workspace_dir,
        experiment_name=experiment_name_obj,
    )
    script_path = (
        custom_script_path.resolve()
        if custom_script_path is not None
        else experiment_paths.apptainer_script_path
    )

    config_path = experiment_paths.config_path
    assert config_path.exists(), (
        f"Did not find `experiment-config.yaml` at '{config_path}'. "
        "Please ensure the experiment name and workspace directory are correct."
    )
    logger.info("Found experiment config file at provided path")

    metadata_dict = experiment_repo.get(config_path=config_path)
    module_names = _extract_all_module_names_from_manifest(metadata_dict)
    check_module_schemas_present(metadata_dict, module_names)

    schemas = {
        m: ModuleSchema.from_dict(metadata_dict["module_schemas"][m])
        for m in set(module_names)
    }
    known_module_names = list(schemas.keys())

    plan = _make_experiment_plan(metadata_dict, schemas)
    data_paths = _with_apptainer_output_root(
        resolve_experiment_data_paths(metadata_dict), experiment_paths
    )
    specs = _build_module_specs(
        plan=plan,
        metadata=metadata_dict,
        schemas=schemas,
        known_module_names=known_module_names,
        data_paths=data_paths,
    )

    execution_plan = build_experiment_execution_plan(
        specs=specs,
        plan=plan,
        metadata=metadata_dict,
        schemas=schemas,
        data_paths=data_paths,
    )

    stages = _build_apptainer_stages(execution_plan)
    mkdir_dirs = _compute_mkdir_dirs(stages)

    workflow_vars = [
        (wf_name, f"WORKFLOW{i + 1}_NAME")
        for i, wf_name in enumerate(plan.workflows.keys())
    ]

    script_content = render_apptainer_script(
        stages=stages,
        execution_plan=execution_plan,
        metadata=metadata_dict,
        data_paths=data_paths,
        workspace_dir=workspace_dir,
        mkdir_dirs=mkdir_dirs,
        workflow_vars=workflow_vars,
    )
    write_apptainer_script(script_content=script_content, script_path=script_path)
    _log_success("Generated Apptainer script: %s", script_path)
    return GenerateApptainerOutput(script_path=script_path)
