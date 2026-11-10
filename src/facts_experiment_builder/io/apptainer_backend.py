"""ApptainerBackend: ExecutionBackend adapter that writes an Apptainer bash script."""

from dataclasses import dataclass
from pathlib import Path

from facts_experiment_builder.application.backend import RunInfo
from facts_experiment_builder.application.execution_graph import (
    ExecutionGraph,
    Stage,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    APPTAINER_OUTPUT_KEY,
)
from facts_experiment_builder.io.apptainer_service import (
    ApptainerServiceSpec,
    to_apptainer_service,
)
from facts_experiment_builder.io.paths import ExperimentPaths
from facts_experiment_builder.io.write_apptainer import (
    render_apptainer_script,
    write_apptainer_script,
)


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


def _build_apptainer_stages(graph: ExecutionGraph) -> _ApptainerStages:
    """Map ExecutionGraph stages to Apptainer execution stages."""
    stage1 = [
        to_apptainer_service(node.run)
        for node in graph.in_stage(Stage.INDEPENDENT).values()
    ]
    stage2 = [
        to_apptainer_service(node.run, wait_for_files=node.wait_for_files)
        for node in graph.in_stage(Stage.NEEDS_CLIMATE).values()
    ]
    stage3 = [
        to_apptainer_service(
            node.run,
            run_in_background=True,
            pid_var=f"PID_{service_name.upper().replace('-', '_')}",
        )
        for service_name, node in graph.in_stage(Stage.TOTALING).items()
    ]
    # Stage 4 runs after Stage 3 has finished, so per-workflow ESL services see their
    # totaled inputs.
    stage4 = [
        to_apptainer_service(node.run)
        for node in graph.in_stage(Stage.EXTREME_SEALEVEL).values()
    ]
    return _ApptainerStages(
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
        all_specs=stage1 + stage2 + stage3 + stage4,
    )


def _compute_mkdir_dirs(stages: _ApptainerStages) -> list[str]:
    """Collect unique service output directories in stage order."""
    return list(dict.fromkeys(spec.output_dir for spec in stages.all_specs))


class ApptainerBackend:
    """Writes the experiment as an executable Apptainer bash script."""

    output_key = APPTAINER_OUTPUT_KEY

    def default_output_path(self, experiment_paths: ExperimentPaths) -> Path:
        return experiment_paths.apptainer_script_path

    def render(self, graph: ExecutionGraph, info: RunInfo) -> str:
        stages = _build_apptainer_stages(graph)
        return render_apptainer_script(
            stages=stages,
            info=info,
            climate_service_name=graph.climate_service_name,
            mkdir_dirs=_compute_mkdir_dirs(stages),
        )

    def write(self, content: str, path: Path) -> None:
        write_apptainer_script(script_content=content, script_path=path)
