"""Render and write the Apptainer bash script from a Jinja2 template."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined

from facts_experiment_builder.application.backend import RunInfo


def _build_template_context(
    stages: Any,
    info: RunInfo,
    climate_service_name: str | None,
    mkdir_dirs: list[str],
) -> dict[str, Any]:
    """Build the variables the apptainer_experiment.sh.j2 template renders.

    Args:
        stages: _ApptainerStages from io.apptainer_backend (typed Any here because
            apptainer_backend imports this module)
        info: Experiment-level values. info.config gives the top-level params
            (experiment name, years, scenario, nsamps, pipeline-id); info.data_paths,
            the same paths used to build the module specs, gives OUTPUT_DIR,
            SHARED_IN and MODULE_IN; the SIF directory is
            <info.workspace_dir>/apptainer_experiments/sif
        climate_service_name: Name of the climate service, or None if there is none
        mkdir_dirs: Output directories the script creates before running services

    Returns:
        Template context dict. workflow_vars pairs each of info.workflow_names with a
        shell variable name, e.g. ("wf1", "WORKFLOW1_NAME"); climate_wait_files lists
        each Stage 2 wait file once, in stage order; has_workflows is True when there
        are facts-total services (Stage 3).
    """
    # Paths come from the same ExperimentDataPaths used to build the module specs,
    # so OUTPUT_DIR etc. always match the binds.
    data_paths = info.data_paths
    config = info.config
    sif_dir = str(info.workspace_dir / "apptainer_experiments" / "sif")

    climate_wait_files: list[str] = list(
        dict.fromkeys(f for spec in stages.stage2 for f in spec.wait_for_files)
    )
    workflow_vars = [
        (wf_name, f"WORKFLOW{i + 1}_NAME")
        for i, wf_name in enumerate(info.workflow_names)
    ]

    return {
        "workspace_dir": str(info.workspace_dir),
        "experiment_name": str(config.experiment_name),
        "output_dir": data_paths.output_data_location,
        "shared_in": data_paths.shared_input_data,
        "module_in": data_paths.module_specific_input_base,
        "sif_dir": sif_dir,
        "pyear_start": str(config.pyear_start),
        "pyear_end": str(config.pyear_end),
        "pyear_step": str(config.pyear_step),
        "baseyear": str(config.baseyear),
        "scenario": str(config.scenario),
        "nsamps": str(config.nsamps),
        "pipeline_id": str(config.pipeline_id),
        "workflow_vars": workflow_vars,
        "all_specs": stages.all_specs,
        "stage1": stages.stage1,
        "stage2": stages.stage2,
        "stage3": stages.stage3,
        "stage4": stages.stage4,
        "climate_wait_files": climate_wait_files,
        "climate_service_name": climate_service_name or "",
        "mkdir_dirs": mkdir_dirs,
        "has_workflows": bool(stages.stage3),
    }


def render_apptainer_script(
    stages: Any,
    info: RunInfo,
    climate_service_name: str | None,
    mkdir_dirs: list[str],
) -> str:
    """Render the Apptainer bash script template to a string.

    The template is apptainer_experiment.sh.j2 in the package's templates directory.
    It is rendered with StrictUndefined, so a variable missing from the context
    raises jinja2.UndefinedError instead of rendering as empty.

    Args:
        stages: _ApptainerStages from io.apptainer_backend
        info: Experiment-level values: config (top-level params), data_paths,
            workspace_dir (WORKSPACE and the SIF directory) and workflow_names
        climate_service_name: Name of the climate service, or None if there is none
        mkdir_dirs: Output directories the script creates before running services

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
        info=info,
        climate_service_name=climate_service_name,
        mkdir_dirs=mkdir_dirs,
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
