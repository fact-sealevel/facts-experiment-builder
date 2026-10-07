"""Unit tests for generate_apptainer application layer."""

import pytest

from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.application.generate_apptainer import (
    _build_apptainer_stages,
    _compute_mkdir_dirs,
    _with_apptainer_output_root,
)
from facts_experiment_builder.core.module.apptainer_service_spec import (
    ApptainerServiceSpec,
)
from facts_experiment_builder.core.module.arg_specs import (
    ArgumentsSpec,
    InputArgSpec,
    MountSpec,
    OutputFileSpec,
    OutputsSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
    ModuleContainerImage,
)
from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(
    module_name: str,
    uses_climate_file: bool = False,
    output_dir: str = "/output",
    image_url: str = "ghcr.io/fact-sealevel/my-module",
    image_tag: str = "0.1.0",
    climate_step_output: str | None = None,
) -> ModuleServiceSpec:
    inputs = []
    if climate_step_output:
        inputs.append(
            InputArgSpec(
                name="climate-data-file",
                type="str",
                source="module_inputs.inputs.climate_data_file",
                climate_step_output=climate_step_output,
                external_volume=True,
                mount=MountSpec(
                    container_path="/mnt/out", volume="output", transform="filename"
                ),
            )
        )
    schema = ModuleSchema(
        module_name=module_name,
        container_image=f"{image_url}:{image_tag}",
        arguments=ArgumentsSpec(inputs=inputs),
        volumes={},
        uses_climate_file=uses_climate_file,
    )
    components = ModuleServiceSpecComponents(
        module_name=module_name,
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir=f"/input/{module_name}",
            shared_input_dir="/input/shared",
        ),
        output_paths=ModuleOutputPaths(output_dir=output_dir, output_type="global"),
        fingerprint_params={},
        inputs={},
        outputs={},
        image=ModuleContainerImage(image_url=image_url, image_tag=image_tag),
        top_level_params=TopLevelParams(),
    )
    return ModuleServiceSpec(components=components, module_definition=schema)


def _make_spec_with_outputs(
    module_name: str = "fair-temperature",
    output_root: str = "/out",
    output_dir: str | None = None,
    output_container_base: str | None = None,
    filenames: dict[str, str] | None = None,
    extra_output_volume: str | None = None,
) -> ModuleServiceSpec:
    """Spec whose outputs live on the shared output volume (mounted at /mnt/out).

    `filenames` maps output arg name -> filename. Components' outputs hold host paths,
    as build_module_service_spec() resolves them.
    """
    filenames = filenames or {
        "output-climate-file": "climate.nc",
        "output-gsat-file": "gsat.nc",
    }
    output_dir = output_dir or f"{output_root}/{module_name}"
    files = [
        OutputFileSpec(
            name=name,
            type="file",
            source=f"module_inputs.outputs.{name.replace('-', '_')}",
            mount=MountSpec(
                container_path="/mnt/out", volume="output", transform="filename"
            ),
            filename=filename,
            output_type="global",
        )
        for name, filename in filenames.items()
    ]
    if extra_output_volume:
        files.append(
            OutputFileSpec(
                name="other-volume-file",
                type="file",
                source="module_inputs.outputs.other_volume_file",
                mount=MountSpec(
                    container_path="/mnt/other", volume=extra_output_volume
                ),
                filename="other.nc",
                output_type="global",
            )
        )
    schema = ModuleSchema(
        module_name=module_name,
        container_image="ghcr.io/fact-sealevel/x:0.1.0",
        arguments=ArgumentsSpec(outputs=OutputsSpec(files=files)),
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
    )
    outputs = {
        name.replace("-", "_"): f"{output_dir}/{filename}"
        for name, filename in filenames.items()
    }
    if extra_output_volume:
        outputs["other_volume_file"] = f"{output_dir}/other.nc"
    components = ModuleServiceSpecComponents(
        module_name=module_name,
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir=f"/input/{module_name}",
            shared_input_dir="/input/shared",
        ),
        output_paths=ModuleOutputPaths(output_dir=output_dir, output_type="global"),
        fingerprint_params={},
        inputs={},
        outputs=outputs,
        image=ModuleContainerImage(
            image_url="ghcr.io/fact-sealevel/x", image_tag="0.1.0"
        ),
        top_level_params=TopLevelParams(),
        output_container_base=output_container_base,
    )
    return ModuleServiceSpec(components=components, module_definition=schema)


def _make_execution_plan(
    standard_specs: dict | None = None,
    facts_total_specs: dict | None = None,
    esl_specs: dict | None = None,
    climate_service_name: str | None = None,
) -> _ExecutionPlan:
    return _ExecutionPlan(
        standard_specs=standard_specs or {},
        facts_total_specs=facts_total_specs or {},
        esl_specs=esl_specs or {},
        standalone_esl_specs={},
        climate_service_name=climate_service_name,
        suppress_output_types=set(),
    )


# ---------------------------------------------------------------------------
# generate_apptainer_service() unit tests
# ---------------------------------------------------------------------------


def test_generate_apptainer_service_returns_correct_type():
    spec = _make_spec("fair-temperature")
    result = spec.generate_apptainer_service()
    assert isinstance(result, ApptainerServiceSpec)


def test_generate_apptainer_service_service_name():
    spec = _make_spec("fair-temperature")
    result = spec.generate_apptainer_service()
    assert result.service_name == "fair-temperature"


def test_generate_apptainer_service_image_name_is_last_url_segment():
    spec = _make_spec(
        "ipccar5-glaciers", image_url="ghcr.io/fact-sealevel/ipccar5", image_tag="0.1.2"
    )
    result = spec.generate_apptainer_service()
    assert result.image_name == "ipccar5"
    assert result.image_tag == "0.1.2"


def test_generate_apptainer_service_defaults():
    spec = _make_spec("my-module")
    result = spec.generate_apptainer_service()
    assert result.wait_for_files == []
    assert result.run_in_background is False
    assert result.pid_var is None


def test_generate_apptainer_service_background_params():
    spec = _make_spec("facts-total-wf1-global")
    result = spec.generate_apptainer_service(run_in_background=True, pid_var="PID_WF1")
    assert result.run_in_background is True
    assert result.pid_var == "PID_WF1"


def test_generate_apptainer_service_wait_for_files_passthrough():
    spec = _make_spec("fittedismip-gris")
    files = ["/output/fair-temperature/climate.nc"]
    result = spec.generate_apptainer_service(wait_for_files=files)
    assert result.wait_for_files == files


# ---------------------------------------------------------------------------
# _build_apptainer_stages() staging tests
# ---------------------------------------------------------------------------


def test_stage1_contains_non_climate_modules():
    climate = _make_spec("fair-temperature", uses_climate_file=False)
    sealevel_indep = _make_spec("ssp-lws", uses_climate_file=False)
    plan = _make_execution_plan(
        standard_specs={
            "fair-temperature": climate,
            "ssp-lws": sealevel_indep,
        },
        climate_service_name="fair-temperature",
    )
    stages = _build_apptainer_stages(plan)

    assert len(stages.stage1) == 2
    assert len(stages.stage2) == 0
    names = {s.service_name for s in stages.stage1}
    assert names == {"fair-temperature", "ssp-lws"}


def test_stage2_contains_climate_dependent_modules():
    climate = _make_spec("fair-temperature", uses_climate_file=False)
    sealevel_dep = _make_spec("fittedismip-gris", uses_climate_file=True)
    plan = _make_execution_plan(
        standard_specs={
            "fair-temperature": climate,
            "fittedismip-gris": sealevel_dep,
        },
        climate_service_name="fair-temperature",
    )
    stages = _build_apptainer_stages(plan)

    assert len(stages.stage1) == 1
    assert stages.stage1[0].service_name == "fair-temperature"
    assert len(stages.stage2) == 1
    assert stages.stage2[0].service_name == "fittedismip-gris"


def test_stage3_specs_have_run_in_background_and_pid_var():
    from facts_experiment_builder.core.workflow import Workflow

    ft_spec = _make_spec("facts-total-wf1f-global")
    wf = Workflow(name="wf1f", module_names=["fair-temperature"])
    plan = _make_execution_plan(
        facts_total_specs={"facts-total-wf1f-global": (ft_spec, wf)},
    )
    stages = _build_apptainer_stages(plan)

    assert len(stages.stage3) == 1
    spec = stages.stage3[0]
    assert spec.run_in_background is True
    assert spec.pid_var is not None
    assert "FACTS_TOTAL_WF1F_GLOBAL" in spec.pid_var


def test_stage4_specs_have_run_in_background_false():
    esl_spec = _make_spec("extremesealevel-wf1f")
    plan = _make_execution_plan(
        esl_specs={"extremesealevel-wf1f": (esl_spec, "facts-total-wf1f-local")},
    )
    stages = _build_apptainer_stages(plan)

    assert len(stages.stage4) == 1
    assert stages.stage4[0].run_in_background is False


def test_all_specs_is_flat_ordered_list():
    climate = _make_spec("fair-temperature", uses_climate_file=False)
    sealevel = _make_spec("fittedismip-gris", uses_climate_file=True)
    plan = _make_execution_plan(
        standard_specs={
            "fair-temperature": climate,
            "fittedismip-gris": sealevel,
        },
        climate_service_name="fair-temperature",
    )
    stages = _build_apptainer_stages(plan)

    assert (
        stages.all_specs
        == stages.stage1 + stages.stage2 + stages.stage3 + stages.stage4
    )


# ---------------------------------------------------------------------------
# host_output_paths() and Stage 2 wait files
# ---------------------------------------------------------------------------


def test_host_output_paths_are_output_dir_plus_filename():
    spec = _make_spec_with_outputs()
    assert spec.host_output_paths() == {
        "output-climate-file": "/out/fair-temperature/climate.nc",
        "output-gsat-file": "/out/fair-temperature/gsat.nc",
    }


def test_host_output_paths_match_container_paths_through_output_mount():
    """Host and container paths name the same file: the output volume mounts the
    parent of output_dir at /mnt/out."""
    spec = _make_spec_with_outputs()
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
    spec = _make_spec_with_outputs(
        module_name="facts-total-wf1-global",
        output_dir="/out/facts-total",
        output_container_base="/mnt/total_out/facts-total",
        filenames={"output-path": "wf1-global.nc"},
    )
    assert spec.host_output_paths() == {"output-path": "/out/facts-total/wf1-global.nc"}


def test_host_output_paths_skips_outputs_on_other_volumes():
    spec = _make_spec_with_outputs(extra_output_volume="other")
    assert "other-volume-file" not in spec.host_output_paths()


def test_stage2_waits_for_the_climate_output_it_declares():
    climate = _make_spec_with_outputs()
    sealevel = _make_spec(
        "tlm-sterodynamics",
        uses_climate_file=True,
        climate_step_output="output-gsat-file",
    )
    plan = _make_execution_plan(
        standard_specs={"fair-temperature": climate, "tlm-sterodynamics": sealevel},
        climate_service_name="fair-temperature",
    )
    stages = _build_apptainer_stages(plan)
    assert stages.stage2[0].wait_for_files == ["/out/fair-temperature/gsat.nc"]


def test_stage2_without_climate_module_has_no_wait_files():
    sealevel = _make_spec(
        "tlm-sterodynamics",
        uses_climate_file=True,
        climate_step_output="output-gsat-file",
    )
    plan = _make_execution_plan(standard_specs={"tlm-sterodynamics": sealevel})
    stages = _build_apptainer_stages(plan)
    assert stages.stage2[0].wait_for_files == []


# ---------------------------------------------------------------------------
# _compute_mkdir_dirs() tests
# ---------------------------------------------------------------------------


def test_compute_mkdir_dirs_lists_each_service_output_dir():
    spec_a = _make_spec("fair-temperature", output_dir="/output/fair-temperature")
    spec_b = _make_spec("ssp-lws", output_dir="/output/ssp-lws")
    plan = _make_execution_plan(
        standard_specs={"fair-temperature": spec_a, "ssp-lws": spec_b},
    )
    dirs = _compute_mkdir_dirs(_build_apptainer_stages(plan))
    assert dirs == ["/output/fair-temperature", "/output/ssp-lws"]


def test_compute_mkdir_dirs_deduplicates_shared_facts_total_dir():
    from facts_experiment_builder.core.workflow import Workflow

    wf = Workflow(name="wf1f", module_names=["fair-temperature"])
    plan = _make_execution_plan(
        facts_total_specs={
            "facts-total-wf1f-global": (
                _make_spec("facts-total-wf1f-global", output_dir="/output/facts-total"),
                wf,
            ),
            "facts-total-wf1f-local": (
                _make_spec("facts-total-wf1f-local", output_dir="/output/facts-total"),
                wf,
            ),
        },
    )
    dirs = _compute_mkdir_dirs(_build_apptainer_stages(plan))
    assert dirs == ["/output/facts-total"]


# ---------------------------------------------------------------------------
# Standalone ESL (no workflows) and registry
# ---------------------------------------------------------------------------


def test_standalone_esl_specs_run_in_stage4_and_get_output_dirs():
    esl = _make_spec("extremesealevel-pointsoverthreshold", output_dir="/output/esl")
    plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={},
        standalone_esl_specs={"extremesealevel-pointsoverthreshold": esl},
        climate_service_name=None,
        suppress_output_types=set(),
    )
    stages = _build_apptainer_stages(plan)
    assert [s.service_name for s in stages.stage4] == [
        "extremesealevel-pointsoverthreshold"
    ]
    assert stages.stage4[0].run_in_background is False
    assert "/output/esl" in _compute_mkdir_dirs(stages)


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
    spec = _make_spec("m", image_url=image_url, image_tag="0.1.2")
    result = spec.generate_apptainer_service()
    assert result.registry == registry
    assert result.image_name == image_name
    assert result.image_ref == image_ref


def test_mixed_registries_keep_each_images_own_reference():
    plan = _make_execution_plan(
        standard_specs={
            "a": _make_spec("a", image_url="ghcr.io/fact-sealevel/a"),
            "b": _make_spec("b", image_url="docker.io/other/b"),
        }
    )
    refs = [s.image_ref for s in _build_apptainer_stages(plan).all_specs]
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
