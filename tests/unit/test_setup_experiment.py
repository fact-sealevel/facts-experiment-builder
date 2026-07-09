import yaml
from unittest.mock import patch
from facts_experiment_builder.application.setup_experiment import (
    hydrate_experiment,
    hydrate_sealevel_step,
    # experiment_name_contains_parent_dir,
    check_if_experiment_already_exists,
)
from facts_experiment_builder.infra.write_experiment_metadata import format_module_value
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
    collect_metadata_param_keys,
)
from facts_experiment_builder.application.setup_experiment import (
    is_totaling_needed,
)
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)
import pytest


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


# --- Testing setup experiment utility fns ---


# def test_experiment_name_contains_parent_dir_fails_when_no_parent():
#    experiment_name = "test-experiment-name"

#    with pytest.raises(ValueError):
#        experiment_name_contains_parent_dir(experiment_name)


def test_check_if_experiment_already_exists_raises_error_correctly(tmp_path):
    experiment_directory = tmp_path / "experiments/my_experiment"
    experiment_directory.mkdir(parents=True)

    with pytest.raises(ExperimentAlreadyExistsError):
        check_if_experiment_already_exists(path_to_experiment=experiment_directory)


def test_check_if_experiment_already_exists_succeeds_correctly(tmp_path):
    experiment_directory = tmp_path / "experiments/my_experiment"
    # create_experiment_directory(experiment_directory=experiment_directory)
    check_if_experiment_already_exists(path_to_experiment=experiment_directory)


# def test_experiment_name_contains_parent_dir_succeeds():
#    experiment_name = "experiments/experiment_name"
#    result = experiment_name_contains_parent_dir(experiment_name=experiment_name)
#    assert result == experiment_name
#    assert result is not None


def test_is_totaling_needed_returns_false_if_less_than_2_sealevel_modules():
    sealevel_step_opts = ["bamber19-icesheets", "", "fair-temperature,,"]
    for sealevel_step in sealevel_step_opts:
        result = is_totaling_needed(sealevel_step=sealevel_step)
        assert result is False, f"Result for {sealevel_step} is {result}"


def test_is_totaling_needed_true_if_more_than_2_sealevel_modules():
    sealevel_step = "bamber19-icesheets,kopp14-verticallandmotion,tlm-sterodynamics"
    result = is_totaling_needed(sealevel_step=sealevel_step)
    print(f"Result for {sealevel_step} is {result}")
    assert result is True


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
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_experiment_climate_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("fair-temperature")
    skeleton = make_skeleton(climate_module="fair-temperature")

    climate, _, _, _ = hydrate_experiment(skeleton)

    assert climate.module_spec is not None
    assert climate.module_spec.module_name == "fair-temperature"


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_experiment_totaling_module_produces_module_spec(mock_load):
    mock_load.return_value = make_module_schema("facts-total")
    skeleton = make_skeleton(totaling_module="facts-total", sealevel_modules=[])

    _, _, totaling, _ = hydrate_experiment(skeleton)

    assert totaling.module_spec is not None
    assert totaling.module_spec.module_name == "facts-total"


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
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
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
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
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
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
    skeleton = make_skeleton(sealevel_modules=["emulandice-ais"])

    step = hydrate_sealevel_step(
        skeleton,
        climate_files={"emulandice-ais": "fair-temperature/climate.nc"},
    )

    inputs = step.module_specs_list[0].to_dict().get("inputs", {})
    assert (
        inputs.get("input_data_file", {}).get("value") == "fair-temperature/climate.nc"
    )
    assert "climate_data_file" not in inputs


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
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


# --- top_level_context threading ---


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_sealevel_step_passes_top_level_context_to_specs(mock_load):
    """top_level_context (e.g. pyear_end) must reach ModuleExperimentSpec so
    multi-key filename_map resolution can use it."""
    schema = ModuleSchema(
        module_name="emulandice2-ais",
        container_image="test/image:latest",
        arguments={
            "inputs": [
                {
                    "name": "emu-file",
                    "source": "module_inputs.inputs.emu_file",
                    "optional": True,
                    "help": "Emulation file",
                    "filename_map": {
                        "keys": ["pyear_end", "region"],
                        "map": {2300: {"ALL": "AIS_ALL_2300.RData"}},
                    },
                    "mount": {"volume": "mod_in", "container_path": "/mnt/in"},
                }
            ],
            "options": [
                {
                    "name": "region",
                    "source": "module_inputs.options.region",
                    "optional": False,
                    "default_value": "ALL",
                }
            ],
            "outputs": {"files": [], "other": []},
            "top_level": [],
            "fingerprint_params": [],
        },
        volumes={},
    )
    mock_load.return_value = schema
    skeleton = make_skeleton(sealevel_modules=["emulandice2-ais"])

    step = hydrate_sealevel_step(
        skeleton,
        top_level_context={"pyear_end": 2300, "pyear-end": 2300},
    )

    emu_bundle = step.module_specs_list[0].inputs.get("emu_file", {})
    assert emu_bundle.get("filename") == "AIS_ALL_2300.RData"


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


def test_format_module_value_empty_dict_roundtrips_as_empty_dict():
    """An empty dict value (e.g. outputs: {}) must serialise as 'key: {}' so YAML
    reads it back as an empty dict rather than None.

    Regression test for the bug where extremesealevel-pointsoverthreshold.outputs
    (which has no outputs) was serialised as a bare 'outputs:' key, causing YAML
    to parse it as None and the adapter to raise a ValueError.
    """
    lines = format_module_value("outputs", {})
    rendered = "\n".join(lines)
    parsed = yaml.safe_load(rendered)
    assert parsed == {"outputs": {}}, f"Expected {{'outputs': {{}}}}, got: {parsed}"


# --- climate_output_type integration ---


def _make_climate_schema(module_name: str) -> ModuleSchema:
    return ModuleSchema(
        module_name=module_name,
        container_image="img:tag",
        arguments={
            "outputs": {
                "files": [
                    {
                        "name": "output-climate-file",
                        "filename": "climate.nc",
                        "output_type": "global",
                    },
                    {
                        "name": "output-gsat-file",
                        "filename": "gsat.nc",
                        "output_type": "global",
                    },
                ]
            }
        },
        volumes={},
    )


def _make_sealevel_schema(module_name: str, climate_output_type: str) -> ModuleSchema:
    return ModuleSchema(
        module_name=module_name,
        container_image="img:tag",
        uses_climate_file=True,
        arguments={
            "inputs": [
                {
                    "name": "climate-data-file",
                    "source": "module_inputs.inputs.climate_data_file",
                    "climate_step_output": climate_output_type,
                    "mount": {"volume": "output", "container_path": "/mnt/out"},
                }
            ],
            "outputs": {},
        },
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
    )


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_experiment_prefills_climate_file_from_climate_module(mock_load):
    """Sealevel module gets climate-data-file = '{climate_module}/{filename}' derived
    from climate_output_type on the sealevel schema."""
    mock_load.side_effect = [
        _make_climate_schema("fair-temperature"),  # climate module load
        _make_sealevel_schema(
            "bamber19-icesheets", "output-climate-file"
        ),  # sealevel load
    ]
    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["bamber19-icesheets"],
    )

    _, sealevel, _, _ = hydrate_experiment(skeleton)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value")
        == "fair-temperature/climate.nc"
    )


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_experiment_prefills_correct_file_for_different_climate_module(
    mock_load,
):
    """When the climate module changes, the prefilled path prefix changes accordingly."""
    mock_load.side_effect = [
        _make_climate_schema("fair2-climate"),
        _make_sealevel_schema("bamber19-icesheets", "output-climate-file"),
    ]
    skeleton = make_skeleton(
        climate_module="fair2-climate",
        sealevel_modules=["bamber19-icesheets"],
    )

    _, sealevel, _, _ = hydrate_experiment(skeleton)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value") == "fair2-climate/climate.nc"
    )


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_experiment_prefills_gsat_file_for_sealevel_module_expecting_gsat(
    mock_load,
):
    """Sealevel module with climate_output_type='output-gsat-file' gets the gsat output."""
    mock_load.side_effect = [
        _make_climate_schema("fair-temperature"),
        _make_sealevel_schema("gsat-module", "output-gsat-file"),
    ]
    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["gsat-module"],
    )

    _, sealevel, _, _ = hydrate_experiment(skeleton)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value") == "fair-temperature/gsat.nc"
    )


@patch(
    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
)
def test_hydrate_experiment_prefills_per_module_independently(mock_load):
    """Two sealevel modules with different climate_output_type each get the right file."""
    mock_load.side_effect = [
        _make_climate_schema("fair-temperature"),  # climate load
        _make_sealevel_schema("module-a", "output-climate-file"),  # sealevel loads
        _make_sealevel_schema("module-b", "output-gsat-file"),
    ]
    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["module-a", "module-b"],
    )

    _, sealevel, _, _ = hydrate_experiment(skeleton)

    inputs_a = sealevel.module_specs_list[0].inputs
    inputs_b = sealevel.module_specs_list[1].inputs
    assert (
        inputs_a.get("climate_data_file", {}).get("value")
        == "fair-temperature/climate.nc"
    )
    assert (
        inputs_b.get("climate_data_file", {}).get("value") == "fair-temperature/gsat.nc"
    )
