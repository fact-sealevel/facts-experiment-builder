from unittest.mock import patch

from facts_experiment_builder.application.setup_new_experiment import (
    hydrate_experiment,
    hydrate_sealevel_step,
)
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema


def make_module_schema(name="test-module", uses_climate_file=False) -> ModuleSchema:
    return ModuleSchema(
        module_name=name,
        container_image="test/image:latest",
        arguments={"inputs": [], "options": [], "outputs": [], "top_level": []},
        volumes={},
        uses_climate_file=uses_climate_file,
    )


def make_skeleton(
    climate_module=None,
    climate_data=None,
    sealevel_modules=None,
    supplied_totaled_sealevel_step_data=None,
    totaling_module=None,
    extremesealevel_module=None,
) -> ExperimentSkeleton:
    return ExperimentSkeleton(
        climate_module=climate_module,
        climate_data=climate_data,
        sealevel_modules=sealevel_modules or [],
        supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
        totaling_module=totaling_module,
        extremesealevel_module=extremesealevel_module,
    )


# --- hydrate_experiment ---


def test_hydrate_experiment_no_modules_returns_none_steps():
    skeleton = make_skeleton(climate_data="/path/to/climate")
    climate, sealevel, totaling, esl = hydrate_experiment(skeleton)

    assert climate.module_spec is None
    assert climate.alternate_climate_data == "/path/to/climate"
    assert sealevel.module_specs_list == []
    assert totaling.module_spec is None
    assert esl.module_spec is None


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_experiment_climate_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("fair-temperature")
    skeleton = make_skeleton(climate_module="fair-temperature")

    climate, _, _, _ = hydrate_experiment(skeleton)

    assert climate.module_spec is not None
    assert climate.module_spec.module_name == "fair-temperature"


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_experiment_totaling_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("facts-total")
    skeleton = make_skeleton(totaling_module="facts-total", sealevel_modules=[])

    _, _, totaling, _ = hydrate_experiment(skeleton)

    assert totaling.module_spec is not None
    assert totaling.module_spec.module_name == "facts-total"


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_experiment_esl_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("extremesealevel-pointsoverthreshold")
    skeleton = make_skeleton(
        extremesealevel_module="extremesealevel-pointsoverthreshold"
    )

    _, _, _, esl = hydrate_experiment(skeleton)

    assert esl.module_spec is not None
    assert esl.module_spec.module_name == "extremesealevel-pointsoverthreshold"


# --- hydrate_sealevel_step ---


def test_hydrate_sealevel_step_no_modules_uses_supplied_totaled_sealevel_step_data():
    skeleton = make_skeleton(supplied_totaled_sealevel_step_data="/path/to/sealevel")

    step = hydrate_sealevel_step(skeleton)

    assert step.supplied_totaled_sealevel_data == "/path/to/sealevel"
    assert step.module_specs_list == []


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_sealevel_step_loads_schemas_for_each_module(mock_load):
    mock_load.side_effect = [
        make_module_schema("bamber19-icesheets"),
        make_module_schema("deconto21-ais"),
    ]
    skeleton = make_skeleton(sealevel_modules=["bamber19-icesheets", "deconto21-ais"])

    step = hydrate_sealevel_step(skeleton)

    assert len(step.module_specs_list) == 2
    assert step.module_specs_list[0].module_name == "bamber19-icesheets"
    assert step.module_specs_list[1].module_name == "deconto21-ais"


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_sealevel_step_merges_climate_data_into_uses_climate_file_modules(
    mock_load,
):
    mock_load.side_effect = [
        make_module_schema("bamber19-icesheets", uses_climate_file=True),
    ]
    skeleton = make_skeleton(
        sealevel_modules=["bamber19-icesheets"],
        climate_data="/path/to/climate.nc",
    )

    step = hydrate_sealevel_step(skeleton)

    spec = step.module_specs_list[0]
    inputs = spec.to_dict().get("inputs", {})
    climate_field = inputs.get("climate_data_file")
    assert climate_field is not None
    assert climate_field["value"] == "/path/to/climate.nc"


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_sealevel_step_merges_climate_module_output_into_uses_climate_file_modules(
    mock_load,
):
    climate_schema = ModuleSchema(
        module_name="fair-temperature",
        container_image="test/image:latest",
        arguments={
            "inputs": [],
            "options": [],
            "outputs": [{"name": "output-climate-file", "filename": "climate.nc"}],
            "top_level": [],
        },
        volumes={},
        uses_climate_file=False,
    )
    mock_load.side_effect = [
        make_module_schema("bamber19-icesheets", uses_climate_file=True),
        climate_schema,
    ]
    skeleton = make_skeleton(
        sealevel_modules=["bamber19-icesheets"],
        climate_module="fair-temperature",
    )

    step = hydrate_sealevel_step(skeleton)

    spec = step.module_specs_list[0]
    inputs = spec.to_dict().get("inputs", {})
    climate_field = inputs.get("climate_data_file")
    assert climate_field is not None
    assert climate_field["value"] == "fair-temperature/climate.nc"


@patch(
    "facts_experiment_builder.application.setup_new_experiment.load_facts_module_by_name"
)
def test_hydrate_sealevel_step_skips_merge_for_modules_without_climate_file(mock_load):
    mock_load.side_effect = [
        make_module_schema("bamber19-icesheets", uses_climate_file=False),
    ]
    skeleton = make_skeleton(
        sealevel_modules=["bamber19-icesheets"],
        climate_data="/path/to/climate.nc",
    )

    step = hydrate_sealevel_step(skeleton)

    spec = step.module_specs_list[0]
    inputs = spec.to_dict().get("inputs", {})
    assert "climate_data_file" not in inputs
