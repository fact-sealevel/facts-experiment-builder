"""Render and write the Apptainer bash script from a Jinja2 template."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined

from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)


def _build_template_context(
    stages: Any,
    execution_plan: _ExecutionPlan,
    metadata: dict[str, Any],
    data_paths: ExperimentDataPaths,
    workspace_dir: Path,
    mkdir_dirs: list[str],
    workflow_vars: list[tuple[str, str]],
) -> dict[str, Any]:
    """Build the variables the apptainer_experiment.sh.j2 template renders.

    Args:
        stages: _ApptainerStages from generate_apptainer (typed Any here because
            generate_apptainer imports this module)
        execution_plan: Execution plan; only its climate_service_name is used
        metadata: Loaded experiment-config.yaml; top-level params (experiment name,
            years, scenario, nsamps, pipeline-id) are read from it, with "" for any
            that are missing
        data_paths: Experiment-level paths, the same ones used to build the module
            specs; give OUTPUT_DIR, SHARED_IN and MODULE_IN
        workspace_dir: Workspace root; the SIF directory is
            <workspace_dir>/apptainer_experiments/sif
        mkdir_dirs: Output directories the script creates before running services
        workflow_vars: (workflow name, shell variable name) pairs, e.g.
            ("wf1", "WORKFLOW1_NAME")

    Returns:
        Template context dict. climate_wait_files lists each Stage 2 wait file once,
        in stage order; has_workflows is True when there are facts-total services
        (Stage 3).
    """
    # Paths come from the same ExperimentDataPaths used to build the module specs,
    # so OUTPUT_DIR etc. always match the binds.
    output_dir = data_paths.output_data_location
    shared_in = data_paths.shared_input_data
    module_in = data_paths.module_specific_input_base
    sif_dir = str(workspace_dir / "apptainer_experiments" / "sif")

    climate_wait_files: list[str] = list(
        dict.fromkeys(f for spec in stages.stage2 for f in spec.wait_for_files)
    )

    return {
        "workspace_dir": str(workspace_dir),
        "experiment_name": str(metadata.get("experiment_name", "")),
        "output_dir": output_dir,
        "shared_in": shared_in,
        "module_in": module_in,
        "sif_dir": sif_dir,
        "pyear_start": str(metadata.get("pyear_start", "")),
        "pyear_end": str(metadata.get("pyear_end", "")),
        "pyear_step": str(metadata.get("pyear_step", "")),
        "baseyear": str(metadata.get("baseyear", "")),
        "scenario": str(metadata.get("scenario", "")),
        "nsamps": str(metadata.get("nsamps", "")),
        "pipeline_id": str(metadata.get("pipeline-id", "")),
        "workflow_vars": workflow_vars,
        "all_specs": stages.all_specs,
        "stage1": stages.stage1,
        "stage2": stages.stage2,
        "stage3": stages.stage3,
        "stage4": stages.stage4,
        "climate_wait_files": climate_wait_files,
        "climate_service_name": execution_plan.climate_service_name or "",
        "mkdir_dirs": mkdir_dirs,
        "has_workflows": bool(stages.stage3),
    }


def render_apptainer_script(
    stages: Any,
    execution_plan: _ExecutionPlan,
    metadata: dict[str, Any],
    data_paths: ExperimentDataPaths,
    workspace_dir: Path,
    mkdir_dirs: list[str],
    workflow_vars: list[tuple[str, str]],
) -> str:
    """Render the Apptainer bash script template to a string.

    The template is apptainer_experiment.sh.j2 in the package's templates directory.
    It is rendered with StrictUndefined, so a variable missing from the context
    raises jinja2.UndefinedError instead of rendering as empty.

    Args:
        stages: _ApptainerStages from generate_apptainer
        execution_plan: Execution plan; only its climate_service_name is used
        metadata: Loaded experiment-config.yaml, for the script's top-level params
        data_paths: Experiment-level paths used to build the module specs
        workspace_dir: Workspace root, used for WORKSPACE and the SIF directory
        mkdir_dirs: Output directories the script creates before running services
        workflow_vars: (workflow name, shell variable name) pairs

    Returns:
        The script's content. See _build_template_context() for how the arguments
        map to template variables.
    """
    env = Environment(
        loader=PackageLoader("facts_experiment_builder", "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    context = _build_template_context(
        stages=stages,
        execution_plan=execution_plan,
        metadata=metadata,
        data_paths=data_paths,
        workspace_dir=workspace_dir,
        mkdir_dirs=mkdir_dirs,
        workflow_vars=workflow_vars,
    )
    return env.get_template("apptainer_experiment.sh.j2").render(**context)


def write_apptainer_script(script_content: str, script_path: Path) -> None:
    """Write script_content to script_path and make it executable.

    Overwrites any existing file at script_path. Adds read and execute permission
    for everyone and write permission for the owner (0o755) to the file's current
    mode.

    Args:
        script_content: Script text, from render_apptainer_script()
        script_path: Where to write the script; its parent directory must exist
    """
    script_path.write_text(script_content)
    script_path.chmod(script_path.stat().st_mode | 0o755)
