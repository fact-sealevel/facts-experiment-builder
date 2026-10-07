"""Unit tests for write_apptainer (template rendering and file writing)."""

import os
import stat

import pytest

from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.application.generate_apptainer import _ApptainerStages
from facts_experiment_builder.core.module.apptainer_service_spec import ApptainerServiceSpec
from facts_experiment_builder.io.write_apptainer import render_apptainer_script, write_apptainer_script


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_apptainer_spec(
    service_name: str = "fair-temperature",
    image_name: str = "fair-temperature",
    image_tag: str = "0.2.1",
    binds: list[str] | None = None,
    args: list[str] | None = None,
    wait_for_files: list[str] | None = None,
    run_in_background: bool = False,
    pid_var: str | None = None,
) -> ApptainerServiceSpec:
    return ApptainerServiceSpec(
        service_name=service_name,
        image_name=image_name,
        image_tag=image_tag,
        binds=binds or ["/input:/mnt/module_specific_in", "/output:/mnt/out"],
        args=args or ["--pipeline-id=abc", "--nsamps=100"],
        wait_for_files=wait_for_files or [],
        run_in_background=run_in_background,
        pid_var=pid_var,
    )


def _make_stages(
    stage1: list | None = None,
    stage2: list | None = None,
    stage3: list | None = None,
    stage4: list | None = None,
) -> _ApptainerStages:
    s1 = stage1 or []
    s2 = stage2 or []
    s3 = stage3 or []
    s4 = stage4 or []
    return _ApptainerStages(
        stage1=s1,
        stage2=s2,
        stage3=s3,
        stage4=s4,
        all_specs=s1 + s2 + s3 + s4,
    )


def _make_execution_plan(climate_service_name: str | None = None) -> _ExecutionPlan:
    return _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={},
        standalone_esl_specs={},
        climate_service_name=climate_service_name,
        suppress_output_types=set(),
    )


_BASE_METADATA = {
    "output-data-location": "/workspace/output",
    "shared-input-data": "/workspace/data/shared",
    "module-specific-input-data": "/workspace/data/module_specific",
    "experiment_name": "test_experiment",
    "pyear_start": 2020,
    "pyear_end": 2150,
    "pyear_step": 10,
    "baseyear": 2005,
    "scenario": "ssp585",
    "nsamps": 1000,
    "pipeline-id": "abc123",
}


def _render(stages=None, execution_plan=None, metadata=None, workspace_dir=None, mkdir_dirs=None):
    from pathlib import Path
    return render_apptainer_script(
        stages=stages or _make_stages(stage1=[_make_apptainer_spec()]),
        execution_plan=execution_plan or _make_execution_plan(),
        metadata=metadata or _BASE_METADATA,
        workspace_dir=workspace_dir or Path("/workspace"),
        mkdir_dirs=mkdir_dirs or ["/workspace/output/fair-temperature"],
        registry="ghcr.io/fact-sealevel",
        workflow_vars=[],
    )


# ---------------------------------------------------------------------------
# Rendering tests
# ---------------------------------------------------------------------------

def test_rendered_script_starts_with_shebang():
    result = _render()
    assert result.startswith("#!/usr/bin/env bash")


def test_rendered_script_has_set_euo_pipefail():
    result = _render()
    assert "set -euo pipefail" in result


def test_stage1_module_appears_in_output():
    spec = _make_apptainer_spec("fair-temperature", args=["--pipeline-id=abc", "--nsamps=100"])
    stages = _make_stages(stage1=[spec])
    result = _render(stages=stages)
    assert "fair-temperature" in result
    assert "--pipeline-id=abc" in result


def test_stage3_nonempty_contains_background_operator():
    ft_spec = _make_apptainer_spec(
        service_name="facts-total-wf1f-global",
        image_name="facts-total",
        args=["--item=/mnt/total_out/module/file.nc", "--output-path=/mnt/total_out/facts-total/out.nc"],
        run_in_background=True,
        pid_var="PID_FACTS_TOTAL_WF1F_GLOBAL",
    )
    stages = _make_stages(stage3=[ft_spec])
    result = _render(stages=stages)
    assert " &" in result
    assert "wait $PID_FACTS_TOTAL_WF1F_GLOBAL" in result


def test_stage3_empty_no_background_operator():
    spec = _make_apptainer_spec("fair-temperature", args=["--pipeline-id=abc", "--nsamps=100"])
    stages = _make_stages(stage1=[spec])
    result = _render(stages=stages)
    assert " &\n" not in result


def test_stage2_wait_for_output_appears():
    s2_spec = _make_apptainer_spec(
        "fittedismip-gris",
        args=["--pipeline-id=abc", "--nsamps=100"],
        wait_for_files=["/workspace/output/fair-temperature/climate.nc"],
    )
    stages = _make_stages(stage2=[s2_spec])
    plan = _make_execution_plan(climate_service_name="fair-temperature")
    result = _render(stages=stages, execution_plan=plan)
    assert "wait_for_output" in result
    assert "/workspace/output/fair-temperature/climate.nc" in result


def test_pull_image_uses_versioned_sif_name():
    spec = _make_apptainer_spec("fair-temperature", image_tag="0.2.1")
    stages = _make_stages(stage1=[spec])
    result = _render(stages=stages)
    assert 'pull_image "fair-temperature-0.2.1"' in result


def test_run_service_uses_versioned_sif_name():
    spec = _make_apptainer_spec("fair-temperature", image_tag="0.2.1", args=["--nsamps=100"])
    stages = _make_stages(stage1=[spec])
    result = _render(stages=stages)
    assert 'run_service "fair-temperature-0.2.1"' in result


def test_workflow_vars_appear_in_header():
    from pathlib import Path
    stages = _make_stages(stage1=[_make_apptainer_spec()])
    result = render_apptainer_script(
        stages=stages,
        execution_plan=_make_execution_plan(),
        metadata=_BASE_METADATA,
        workspace_dir=Path("/workspace"),
        mkdir_dirs=[],
        registry="ghcr.io/fact-sealevel",
        workflow_vars=[("wf1f", "WORKFLOW1_NAME"), ("wf2f", "WORKFLOW2_NAME")],
    )
    assert 'WORKFLOW1_NAME="wf1f"' in result
    assert 'WORKFLOW2_NAME="wf2f"' in result


# ---------------------------------------------------------------------------
# write_apptainer_script() tests
# ---------------------------------------------------------------------------

def test_write_apptainer_script_creates_file(tmp_path):
    script_path = tmp_path / "experiment-apptainer.sh"
    write_apptainer_script("#!/usr/bin/env bash\necho hello\n", script_path)
    assert script_path.exists()
    assert script_path.read_text() == "#!/usr/bin/env bash\necho hello\n"


def test_write_apptainer_script_sets_executable_bit(tmp_path):
    script_path = tmp_path / "experiment-apptainer.sh"
    write_apptainer_script("#!/usr/bin/env bash\n", script_path)
    assert os.access(script_path, os.X_OK)
