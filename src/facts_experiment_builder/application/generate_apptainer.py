#!/usr/bin/env python3
"""Generate Apptainer bash script from experiment config."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from facts_experiment_builder.application.execution_plan import (
    _ExecutionPlan,
    _ModuleSpecs,
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
from facts_experiment_builder.core.module.apptainer_service_spec import ApptainerServiceSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema
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
    stage3: list[ApptainerServiceSpec]  # facts-total × workflow × output_type (parallel)
    stage4: list[ApptainerServiceSpec]  # ESL × workflow (sequential)
    all_specs: list[ApptainerServiceSpec]  # stage1+2+3+4; ordered for pull + mkdir


@dataclass(frozen=True)
class GenerateApptainerOutput:
    script_path: Path


def _log_success(msg: str, *args: object) -> None:
    logger.log(_SUCCESS, msg, *args)


def _get_climate_wait_files(
    spec: ModuleServiceSpec,
    climate_spec: ModuleServiceSpec,
    output_dir: str,
) -> list[str]:
    """Return host paths this spec must wait for from the climate module's outputs.

    Iterates the spec's InputArgSpec entries with climate_step_output set, looks up
    the matching output arg in the climate module's generated args, and converts the
    container path to a host path via the output volume mount (/mnt/out → output_dir).
    """
    needed: set[str] = set()
    for inp in spec.module_definition.arguments.inputs:
        if inp.climate_step_output:
            needed.add(inp.climate_step_output)
    if not needed:
        return []

    climate_args = climate_spec._build_command_args()
    host_paths: list[str] = []
    for arg in climate_args:
        if not arg.startswith("--"):
            continue
        rest = arg[2:]
        if "=" not in rest:
            continue
        arg_name, value = rest.split("=", 1)
        if arg_name in needed and value.startswith("/mnt/out/"):
            host_path = output_dir.rstrip("/") + value[len("/mnt/out"):]
            host_paths.append(host_path)
    return host_paths




def _build_apptainer_stages(
    execution_plan: _ExecutionPlan,
    metadata: dict[str, Any],
) -> _ApptainerStages:
    """Map _ExecutionPlan fields to Apptainer execution stages."""
    output_dir = str(metadata.get("output-data-location", ""))
    climate_service_name = execution_plan.climate_service_name
    climate_spec: ModuleServiceSpec | None = (
        execution_plan.standard_specs.get(climate_service_name)
        if climate_service_name
        else None
    )

    stage1: list[ApptainerServiceSpec] = []
    stage2: list[ApptainerServiceSpec] = []
    for service_name, spec in execution_plan.standard_specs.items():
        if not spec.module_definition.uses_climate_file:
            stage1.append(
                spec.generate_apptainer_service(
                    suppress_output_types=execution_plan.suppress_output_types,
                )
            )
        else:
            wait_files = (
                _get_climate_wait_files(spec, climate_spec, output_dir)
                if climate_spec
                else []
            )
            stage2.append(
                spec.generate_apptainer_service(
                    wait_for_files=wait_files,
                    suppress_output_types=execution_plan.suppress_output_types,
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

    stage4: list[ApptainerServiceSpec] = []
    for _service_name, (spec, _depends_on) in execution_plan.esl_specs.items():
        stage4.append(spec.generate_apptainer_service())

    all_specs = stage1 + stage2 + stage3 + stage4
    return _ApptainerStages(
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
        all_specs=all_specs,
    )


def _compute_mkdir_dirs(execution_plan: _ExecutionPlan) -> list[str]:
    """Collect unique module output directories in stage order."""
    seen: set[str] = set()
    dirs: list[str] = []

    sources: list[ModuleServiceSpec] = list(execution_plan.standard_specs.values())
    for spec, _ in execution_plan.facts_total_specs.values():
        sources.append(spec)
    for spec, _ in execution_plan.esl_specs.values():
        sources.append(spec)
    for spec in execution_plan.standalone_esl_specs.values():
        sources.append(spec)

    for spec in sources:
        d = spec.components.output_paths.output_dir
        if d not in seen:
            seen.add(d)
            dirs.append(d)
    return dirs


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
    specs = _build_module_specs(
        plan=plan,
        metadata=metadata_dict,
        schemas=schemas,
        known_module_names=known_module_names,
    )

    execution_plan = build_experiment_execution_plan(
        specs=specs,
        plan=plan,
        metadata=metadata_dict,
        schemas=schemas,
    )

    stages = _build_apptainer_stages(execution_plan, metadata_dict)
    mkdir_dirs = _compute_mkdir_dirs(execution_plan)

    registry = ""
    for spec in execution_plan.standard_specs.values():
        registry = spec.components.image.image_url.rstrip("/").rsplit("/", 1)[0]
        break

    workflow_vars = [
        (wf_name, f"WORKFLOW{i + 1}_NAME")
        for i, wf_name in enumerate(plan.workflows.keys())
    ]

    script_content = render_apptainer_script(
        stages=stages,
        execution_plan=execution_plan,
        metadata=metadata_dict,
        workspace_dir=workspace_dir,
        mkdir_dirs=mkdir_dirs,
        registry=registry,
        workflow_vars=workflow_vars,
    )
    write_apptainer_script(script_content=script_content, script_path=script_path)
    _log_success("Generated Apptainer script: %s", script_path)
    return GenerateApptainerOutput(script_path=script_path)
