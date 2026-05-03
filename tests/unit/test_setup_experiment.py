from unittest.mock import patch
from facts_experiment_builder.application.setup_experiment import (
    hydrate_experiment,
    hydrate_sealevel_step,
)
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
    collect_metadata_param_keys,
)


def make_module_schema(name="test-module", uses_climate_file=False) -> ModuleSchema:
    return ModuleSchema(
        module_name=name,
        container_image="test/image:latest",
        arguments={"inputs": [], "options": [], "outputs": {}, "top_level": []},
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
    "facts_experiment_builder.application.setup_experiment.load_facts_module_by_name"
)
def test_hydrate_experiment_climate_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("fair-temperature")
    skeleton = make_skeleton(climate_module="fair-temperature")

    climate, _, _, _ = hydrate_experiment(skeleton)

    assert climate.module_spec is not None
    assert climate.module_spec.module_name == "fair-temperature"


@patch(
    "facts_experiment_builder.application.setup_experiment.load_facts_module_by_name"
)
def test_hydrate_experiment_totaling_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("facts-total")
    skeleton = make_skeleton(totaling_module="facts-total", sealevel_modules=[])

    _, _, totaling, _ = hydrate_experiment(skeleton)

    assert totaling.module_spec is not None
    assert totaling.module_spec.module_name == "facts-total"


@patch(
    "facts_experiment_builder.application.setup_experiment.load_facts_module_by_name"
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
    "facts_experiment_builder.application.setup_experiment.load_facts_module_by_name"
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
    "facts_experiment_builder.application.setup_experiment.load_facts_module_by_name"
)
def test_hydrate_sealevel_step_merges_climate_data_using_module_specific_input_key(
    mock_load,
):
    """Modules with a non-standard climate input name (e.g. input-data-file) get the
    climate file path merged under the correct key, not climate_data_file."""
    schema = ModuleSchema(
        module_name="emulandice-ais",
        container_image="test/image:latest",
        arguments={
            "inputs": [
                {
                    "name": "input-data-file",
                    "source": "module_inputs.inputs.input_data_file",
                    "mount": {"volume": "output", "container_path": "/mnt/out"},
                }
            ],
            "options": [],
            "outputs": {},
            "top_level": [],
        },
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
        uses_climate_file=True,
    )
    mock_load.side_effect = [schema]
    skeleton = make_skeleton(
        sealevel_modules=["emulandice-ais"],
        climate_data="fair-temperature/climate.nc",
    )

    step = hydrate_sealevel_step(skeleton)

    inputs = step.module_specs_list[0].to_dict().get("inputs", {})
    assert (
        inputs.get("input_data_file", {}).get("value") == "fair-temperature/climate.nc"
    )
    assert "climate_data_file" not in inputs


@patch(
    "facts_experiment_builder.application.setup_experiment.load_facts_module_by_name"
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


# --- collect_metadata_param_keys ---


def make_schema_with_args(
    name="test-module", top_level=None, fingerprint_params=None
) -> ModuleSchema:
    return ModuleSchema(
        module_name=name,
        container_image="test/image:latest",
        arguments={
            "inputs": [],
            "options": [],
            "outputs": {},
            "top_level": top_level or [],
            "fingerprint_params": fingerprint_params or [],
        },
        volumes={},
    )


def test_collect_metadata_param_keys_top_level_returns_metadata_sourced_keys():
    schema = make_schema_with_args(
        top_level=[
            {
                "name": "pipeline-id",
                "source": "metadata.pipeline-id",
                "help": "Pipeline ID",
            },
            {"name": "baseyear", "source": "metadata.baseyear", "help": "Base year"},
            {
                "name": "chunksize",
                "source": "module_inputs.options.chunksize",
                "help": "Chunk size",
            },
        ]
    )
    result = collect_metadata_param_keys([schema], "top_level")
    assert result == {"pipeline-id": "Pipeline ID", "baseyear": "Base year"}
    assert "chunksize" not in result


def test_collect_metadata_param_keys_fingerprint_params_excludes_module_inputs():
    schema = make_schema_with_args(
        fingerprint_params=[
            {
                "name": "location-file",
                "source": "metadata.location-file",
                "help": "Location file",
            },
            {
                "name": "fingerprint-dir",
                "source": "module_inputs.fingerprint_params.fingerprint_dir",
                "help": "FP dir",
            },
        ]
    )
    result = collect_metadata_param_keys([schema], "fingerprint_params")
    assert result == {"location-file": "Location file"}
    assert "fingerprint-dir" not in result


def test_collect_metadata_param_keys_deduplicates_across_schemas():
    schema_a = make_schema_with_args(
        name="module-a",
        top_level=[
            {"name": "pipeline-id", "source": "metadata.pipeline-id", "help": "From A"}
        ],
    )
    schema_b = make_schema_with_args(
        name="module-b",
        top_level=[
            {"name": "pipeline-id", "source": "metadata.pipeline-id", "help": "From B"},
            {"name": "scenario", "source": "metadata.scenario", "help": "Scenario"},
        ],
    )
    result = collect_metadata_param_keys([schema_a, schema_b], "top_level")
    assert result["pipeline-id"] == "From A"  # first schema wins
    assert result["scenario"] == "Scenario"
    assert len(result) == 2


def test_collect_metadata_param_keys_empty_when_no_metadata_sources():
    schema = make_schema_with_args(
        fingerprint_params=[
            {
                "name": "fingerprint-dir",
                "source": "module_inputs.fingerprint_params.fingerprint_dir",
            },
        ]
    )
    result = collect_metadata_param_keys([schema], "fingerprint_params")
    assert result == {}
