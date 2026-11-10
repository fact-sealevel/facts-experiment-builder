"""Unit tests for the Apptainer adapter (io.apptainer_backend, io.apptainer_service)."""

import pytest

from facts_experiment_builder.application.execution_graph import build_execution_graph
from facts_experiment_builder.io.apptainer_backend import (
    _build_apptainer_stages,
    _compute_mkdir_dirs,
    _with_apptainer_output_root,
)
from facts_experiment_builder.io.apptainer_service import (
    ApptainerServiceSpec,
    to_apptainer_service,
)
from tests.unit.helpers import (
    make_execution_plan,
    make_service_spec,
    make_service_spec_with_outputs,
)


def _stages(plan):
    return _build_apptainer_stages(build_execution_graph(plan))


# ---------------------------------------------------------------------------
# to_apptainer_service() unit tests
# ---------------------------------------------------------------------------


def test_to_apptainer_service_returns_correct_type():
    spec = make_service_spec("fair-temperature")
    result = to_apptainer_service(spec.to_service_run())
    assert isinstance(result, ApptainerServiceSpec)


def test_to_apptainer_service_service_name():
    spec = make_service_spec("fair-temperature")
    result = to_apptainer_service(spec.to_service_run())
    assert result.service_name == "fair-temperature"


def test_to_apptainer_service_image_name_is_last_url_segment():
    spec = make_service_spec(
        "ipccar5-glaciers", image_url="ghcr.io/fact-sealevel/ipccar5", image_tag="0.1.2"
    )
    result = to_apptainer_service(spec.to_service_run())
    assert result.image_name == "ipccar5"
    assert result.image_tag == "0.1.2"


def test_to_apptainer_service_defaults():
    spec = make_service_spec("my-module")
    result = to_apptainer_service(spec.to_service_run())
    assert result.wait_for_files == []
    assert result.run_in_background is False
    assert result.pid_var is None


def test_to_apptainer_service_background_params():
    spec = make_service_spec("facts-total-wf1-global")
    result = to_apptainer_service(
        spec.to_service_run(), run_in_background=True, pid_var="PID_WF1"
    )
    assert result.run_in_background is True
    assert result.pid_var == "PID_WF1"


def test_to_apptainer_service_wait_for_files_passthrough():
    spec = make_service_spec("fittedismip-gris")
    files = ["/output/fair-temperature/climate.nc"]
    result = to_apptainer_service(spec.to_service_run(), wait_for_files=files)
    assert result.wait_for_files == files


# ---------------------------------------------------------------------------
# _build_apptainer_stages() staging tests
# ---------------------------------------------------------------------------


def test_stage1_contains_non_climate_modules():
    climate = make_service_spec("fair-temperature", uses_climate_file=False)
    sealevel_indep = make_service_spec("ssp-lws", uses_climate_file=False)
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": climate,
            "ssp-lws": sealevel_indep,
        },
        climate_service_name="fair-temperature",
    )
    stages = _stages(plan)

    assert len(stages.stage1) == 2
    assert len(stages.stage2) == 0
    names = {s.service_name for s in stages.stage1}
    assert names == {"fair-temperature", "ssp-lws"}


def test_stage2_contains_climate_dependent_modules():
    climate = make_service_spec("fair-temperature", uses_climate_file=False)
    sealevel_dep = make_service_spec("fittedismip-gris", uses_climate_file=True)
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": climate,
            "fittedismip-gris": sealevel_dep,
        },
        climate_service_name="fair-temperature",
    )
    stages = _stages(plan)

    assert len(stages.stage1) == 1
    assert stages.stage1[0].service_name == "fair-temperature"
    assert len(stages.stage2) == 1
    assert stages.stage2[0].service_name == "fittedismip-gris"


def test_stage3_specs_have_run_in_background_and_pid_var():
    from facts_experiment_builder.core.workflow import Workflow

    ft_spec = make_service_spec("facts-total-wf1f-global")
    wf = Workflow(name="wf1f", module_names=["fair-temperature"])
    plan = make_execution_plan(
        facts_total_specs={"facts-total-wf1f-global": (ft_spec, wf)},
    )
    stages = _stages(plan)

    assert len(stages.stage3) == 1
    spec = stages.stage3[0]
    assert spec.run_in_background is True
    assert spec.pid_var is not None
    assert "FACTS_TOTAL_WF1F_GLOBAL" in spec.pid_var


def test_stage4_specs_have_run_in_background_false():
    esl_spec = make_service_spec("extremesealevel-wf1f")
    plan = make_execution_plan(
        esl_specs={"extremesealevel-wf1f": (esl_spec, "facts-total-wf1f-local")},
    )
    stages = _stages(plan)

    assert len(stages.stage4) == 1
    assert stages.stage4[0].run_in_background is False


def test_all_specs_is_flat_ordered_list():
    climate = make_service_spec("fair-temperature", uses_climate_file=False)
    sealevel = make_service_spec("fittedismip-gris", uses_climate_file=True)
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": climate,
            "fittedismip-gris": sealevel,
        },
        climate_service_name="fair-temperature",
    )
    stages = _stages(plan)

    assert (
        stages.all_specs
        == stages.stage1 + stages.stage2 + stages.stage3 + stages.stage4
    )


# ---------------------------------------------------------------------------
# host_output_paths() and Stage 2 wait files
# ---------------------------------------------------------------------------


def test_host_output_paths_are_output_dir_plus_filename():
    spec = make_service_spec_with_outputs()
    assert spec.host_output_paths() == {
        "output-climate-file": "/out/fair-temperature/climate.nc",
        "output-gsat-file": "/out/fair-temperature/gsat.nc",
    }


def test_host_output_paths_match_container_paths_through_output_mount():
    """Host and container paths name the same file: the output volume mounts the
    parent of output_dir at /mnt/out."""
    spec = make_service_spec_with_outputs()
    output_root = "/out"  # parent of output_dir, as mounted by _build_volumes()
    container_args = {
        arg[2:].split("=", 1)[0]: arg.split("=", 1)[1]
        for arg in spec._build_command_args()
        if arg.startswith("--") and "=" in arg
    }
    for name, host_path in spec.host_output_paths().items():
        container_path = container_args[name]
        assert container_path.startswith("/mnt/out/")
        assert host_path == output_root + container_path[len("/mnt/out") :]


def test_host_output_paths_with_output_container_base():
    """facts-total services: container <base>/<file> <-> host <output_dir>/<file>."""
    spec = make_service_spec_with_outputs(
        module_name="facts-total-wf1-global",
        output_dir="/out/facts-total",
        output_container_base="/mnt/total_out/facts-total",
        filenames={"output-path": "wf1-global.nc"},
    )
    assert spec.host_output_paths() == {"output-path": "/out/facts-total/wf1-global.nc"}


def test_host_output_paths_skips_outputs_on_other_volumes():
    spec = make_service_spec_with_outputs(extra_output_volume="other")
    assert "other-volume-file" not in spec.host_output_paths()


def test_stage2_waits_for_the_climate_output_it_declares():
    climate = make_service_spec_with_outputs()
    sealevel = make_service_spec(
        "tlm-sterodynamics",
        uses_climate_file=True,
        climate_step_output="output-gsat-file",
    )
    plan = make_execution_plan(
        standard_specs={"fair-temperature": climate, "tlm-sterodynamics": sealevel},
        climate_service_name="fair-temperature",
    )
    stages = _stages(plan)
    assert stages.stage2[0].wait_for_files == ["/out/fair-temperature/gsat.nc"]


def test_stage2_without_climate_module_has_no_wait_files():
    sealevel = make_service_spec(
        "tlm-sterodynamics",
        uses_climate_file=True,
        climate_step_output="output-gsat-file",
    )
    plan = make_execution_plan(standard_specs={"tlm-sterodynamics": sealevel})
    stages = _stages(plan)
    assert stages.stage2[0].wait_for_files == []


# ---------------------------------------------------------------------------
# _compute_mkdir_dirs() tests
# ---------------------------------------------------------------------------


def test_compute_mkdir_dirs_lists_each_service_output_dir():
    spec_a = make_service_spec(
        "fair-temperature", output_dir="/output/fair-temperature"
    )
    spec_b = make_service_spec("ssp-lws", output_dir="/output/ssp-lws")
    plan = make_execution_plan(
        standard_specs={"fair-temperature": spec_a, "ssp-lws": spec_b},
    )
    dirs = _compute_mkdir_dirs(_stages(plan))
    assert dirs == ["/output/fair-temperature", "/output/ssp-lws"]


def test_compute_mkdir_dirs_deduplicates_shared_facts_total_dir():
    from facts_experiment_builder.core.workflow import Workflow

    wf = Workflow(name="wf1f", module_names=["fair-temperature"])
    plan = make_execution_plan(
        facts_total_specs={
            "facts-total-wf1f-global": (
                make_service_spec(
                    "facts-total-wf1f-global", output_dir="/output/facts-total"
                ),
                wf,
            ),
            "facts-total-wf1f-local": (
                make_service_spec(
                    "facts-total-wf1f-local", output_dir="/output/facts-total"
                ),
                wf,
            ),
        },
    )
    dirs = _compute_mkdir_dirs(_stages(plan))
    assert dirs == ["/output/facts-total"]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "image_url, registry, image_name, image_ref",
    [
        (
            "ghcr.io/fact-sealevel/ipccar5",
            "ghcr.io/fact-sealevel",
            "ipccar5",
            "ghcr.io/fact-sealevel/ipccar5:0.1.2",
        ),
        (
            "docker.io/other-org/tlm",
            "docker.io/other-org",
            "tlm",
            "docker.io/other-org/tlm:0.1.2",
        ),
        ("myimage", "", "myimage", "myimage:0.1.2"),
    ],
)
def test_apptainer_service_image_reference(image_url, registry, image_name, image_ref):
    spec = make_service_spec("m", image_url=image_url, image_tag="0.1.2")
    result = to_apptainer_service(spec.to_service_run())
    assert result.registry == registry
    assert result.image_name == image_name
    assert result.image_ref == image_ref


def test_mixed_registries_keep_each_images_own_reference():
    plan = make_execution_plan(
        standard_specs={
            "a": make_service_spec("a", image_url="ghcr.io/fact-sealevel/a"),
            "b": make_service_spec("b", image_url="docker.io/other/b"),
        }
    )
    refs = [s.image_ref for s in _stages(plan).all_specs]
    assert refs == ["ghcr.io/fact-sealevel/a:0.1.0", "docker.io/other/b:0.1.0"]


# ---------------------------------------------------------------------------
# Apptainer output root
# ---------------------------------------------------------------------------


def _experiment_paths(tmp_path):
    from facts_experiment_builder.core.experiment.name import ExperimentName
    from facts_experiment_builder.io.paths import ExperimentPaths

    return ExperimentPaths(
        workspace_dir=tmp_path, experiment_name=ExperimentName.parse("experiments/exp")
    )


def test_apptainer_output_dir_is_separate_from_compose_output_dir(tmp_path):
    paths = _experiment_paths(tmp_path)
    assert paths.apptainer_output_dir == tmp_path / "experiments/exp/output-apptainer"
    assert paths.apptainer_output_dir != paths.output_dir


def test_with_apptainer_output_root_replaces_only_the_output_root(tmp_path):
    from facts_experiment_builder.core.module.module_service_path_resolution import (
        resolve_experiment_data_paths,
    )

    data_paths = resolve_experiment_data_paths(
        {
            "output-data-location": "/compose/output",
            "shared-input-data": "/data/shared",
            "module-specific-input-data": "/data/module",
            "experiment-specific-input-data": "/data/exp",
        }
    )
    paths = _experiment_paths(tmp_path)
    result = _with_apptainer_output_root(data_paths, paths)
    assert result.output_data_location == str(paths.apptainer_output_dir)
    assert result.shared_input_data == data_paths.shared_input_data
    assert result.module_specific_input_base == data_paths.module_specific_input_base
    assert (
        result.experiment_specific_input_data
        == data_paths.experiment_specific_input_data
    )
