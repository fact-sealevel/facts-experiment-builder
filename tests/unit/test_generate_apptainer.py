"""Unit tests for generate_apptainer application layer."""

import pytest

from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.application.generate_apptainer import (
    _ApptainerStages,
    _build_apptainer_stages,
    _compute_mkdir_dirs,
    _get_climate_wait_files,
)
from facts_experiment_builder.core.module.apptainer_service_spec import ApptainerServiceSpec
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec, InputArgSpec, MountSpec
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
                mount=MountSpec(container_path="/mnt/out", volume="output", transform="filename"),
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
    spec = _make_spec("ipccar5-glaciers", image_url="ghcr.io/fact-sealevel/ipccar5", image_tag="0.1.2")
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
    stages = _build_apptainer_stages(plan, {"output-data-location": "/output"})

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
    stages = _build_apptainer_stages(plan, {"output-data-location": "/output"})

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
    stages = _build_apptainer_stages(plan, {"output-data-location": "/output"})

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
    stages = _build_apptainer_stages(plan, {"output-data-location": "/output"})

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
    stages = _build_apptainer_stages(plan, {"output-data-location": "/output"})

    assert stages.all_specs == stages.stage1 + stages.stage2 + stages.stage3 + stages.stage4


# ---------------------------------------------------------------------------
# _compute_mkdir_dirs() tests
# ---------------------------------------------------------------------------

def test_compute_mkdir_dirs_deduplicates():
    spec_a = _make_spec("fair-temperature", output_dir="/output/fair-temperature")
    spec_b = _make_spec("ssp-lws", output_dir="/output/ssp-lws")
    plan = _make_execution_plan(
        standard_specs={"fair-temperature": spec_a, "ssp-lws": spec_b},
    )
    dirs = _compute_mkdir_dirs(plan)
    assert len(dirs) == len(set(dirs))
    assert "/output/fair-temperature" in dirs
    assert "/output/ssp-lws" in dirs


def test_compute_mkdir_dirs_includes_facts_total():
    from facts_experiment_builder.core.workflow import Workflow

    ft_spec = _make_spec("facts-total-wf1f-global", output_dir="/output/facts-total")
    wf = Workflow(name="wf1f", module_names=["fair-temperature"])
    plan = _make_execution_plan(
        facts_total_specs={"facts-total-wf1f-global": (ft_spec, wf)},
    )
    dirs = _compute_mkdir_dirs(plan)
    assert "/output/facts-total" in dirs
