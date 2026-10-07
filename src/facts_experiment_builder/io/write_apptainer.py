"""Render and write the Apptainer bash script from a Jinja2 template."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined

from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.core.module.module_service_path_resolution import expand_path


def _build_template_context(
    stages: Any,
    execution_plan: _ExecutionPlan,
    metadata: dict[str, Any],
    workspace_dir: Path,
    mkdir_dirs: list[str],
    registry: str,
    workflow_vars: list[tuple[str, str]],
) -> dict[str, Any]:
    output_dir = expand_path(metadata["output-data-location"])
    shared_in = expand_path(metadata["shared-input-data"])
    module_in = expand_path(metadata["module-specific-input-data"])
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
        "registry": registry,
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
    workspace_dir: Path,
    mkdir_dirs: list[str],
    registry: str,
    workflow_vars: list[tuple[str, str]],
) -> str:
    """Render the Apptainer bash script template to a string."""
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
        workspace_dir=workspace_dir,
        mkdir_dirs=mkdir_dirs,
        registry=registry,
        workflow_vars=workflow_vars,
    )
    return env.get_template("apptainer_experiment.sh.j2").render(**context)


def write_apptainer_script(script_content: str, script_path: Path) -> None:
    """Write script_content to script_path and make it executable."""
    script_path.write_text(script_content)
    script_path.chmod(script_path.stat().st_mode | 0o755)
