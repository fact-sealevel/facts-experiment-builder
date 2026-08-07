import yaml
from pathlib import Path
from facts_experiment_builder.application.setup_experiment import (
    PrepareExperimentOutput,
    prepare_experiment_setup,
    finalize_experiment_setup,
)
from facts_experiment_builder.core.module.module_schema import (
    collect_metadata_param_keys,
)
from facts_experiment_builder.core.experiment.skeleton import (
    hydrate_experiment,
)

from facts_experiment_builder.io.write_config import format_module_value
from facts_experiment_builder.core.experiment.skeleton import (
    ExperimentSkeleton,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
)
from tests.unit.helpers import InMemoryModuleDefinitions


# factories to build some test fixtures
def make_schema(
    name="test-module", uses_climate_file=False, arguments=None
) -> ModuleSchema:
    if arguments is None:
        arguments = {
            "inputs": [],
            "options": [],
            "outputs": {"files": [], "other": []},
            "top_level": [],
        }
    return ModuleSchema.from_dict(
        {
            "module_name": name,
            "container_image": "test/image:latest",
            "arguments": arguments,
            "volumes": {},
            "uses_climate_file": uses_climate_file,
        }
    )


def make_skeleton(**overrides) -> ExperimentSkeleton:
    defaults = dict(
        climate_module=None,
        climate_data=None,
        sealevel_modules=[],
        supplied_totaled_sealevel_step_data=None,
        totaling_module=None,
        extremesealevel_module=None,
        module_regions=None,
    )
    return ExperimentSkeleton(**{**defaults, **overrides})


def test_hydrate_experiment_builds_climate_step():
    skeleton = make_skeleton(
        climate_module="fair-temperature", sealevel_modules=["tlm-sterodynamics"]
    )
    schemas = {
        "fair-temperature": make_schema(
            "fair-temperature",
        ),
        "tlm-sterodynamics": make_schema(
            "tlm-sterodynamics",
            uses_climate_file=True,
        ),
    }
    climate_step, sealevel_step, totaling_step, esl_step = hydrate_experiment(
        skeleton=skeleton,
        schemas=schemas,
    )
    assert climate_step.module_name == "fair-temperature"
    assert sealevel_step.module_names == ["tlm-sterodynamics"]


def test_finalize_experiment_setup_writes_metadata_config(tmp_path):
    experiment_name = "fake_experiment_location/experiment_name"
    workspace_dir = Path(tmp_path / "fake_experiment_location")
    workspace_dir.mkdir()

    definitions = InMemoryModuleDefinitions(
        {
            "fair-temperature": make_schema("fair-temperature"),
            "tlm-sterodynamics": make_schema(
                "tlm-sterodynamics", uses_climate_file=True
            ),
            "larmip-ais": make_schema("larmip-ais", uses_climate_file=True),
            "facts-total": make_schema("facts-total"),
        }
    )
    output = prepare_experiment_setup(
        experiment_name=experiment_name,
        module_regions=None,
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step="tlm-sterodynamics,larmip-ais",
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step=None,
        workspace_dir=workspace_dir,
    )
    skeleton = output.experiment_skeleton
    experiment_path = output.experiment_paths
    workflow_dict = {"all-modules": ["tlm-sterodynamics", "larmip-ais"]}

    finalize_experiment_setup(
        experiment_name,
        experiment_path,
        skeleton,
        workflow_dict,
        pipeline_id="abc123",
        scenario="ssp585",
        baseyear=2005,
        pyear_end=2150,
        pyear_step=10,
        pyear_start=2020,
        nsamps=50,
        location_file="location.lst",
        module_specific_input_data="path/to/data",
        shared_input_data="path/to/shared/data",
        projection_scale="local",
        definition=definitions,
    )
    config_path = experiment_path.config_path
    assert config_path.exists()


# --- Testing setup experiment utility fns ---


def test_prepare_experiment_setup_returns_correct_output_type(tmp_path):
    workspace_dir = Path(tmp_path / "fake_experiment_location")
    workspace_dir.mkdir()
    output = prepare_experiment_setup(
        experiment_name="fake_experiment_location/experiment_name",
        module_regions=None,
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step="tlm-sterodynamics,larmip-ais",
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step=None,
        workspace_dir=workspace_dir,
    )
    assert isinstance(output, PrepareExperimentOutput)


# --- hydrate_experiment ---


def test_hydrate_experiment_no_modules_returns_none_steps():
    skeleton = make_skeleton(climate_data="/path/to/climate/data", sealevel_modules=[])
    schemas = make_schema()
    climate, sealevel, totaling, esl = hydrate_experiment(
        skeleton=skeleton, schemas=schemas
    )

    assert climate.module_spec is None
    assert climate.alternate_climate_data == "/path/to/climate/data"
    assert sealevel.module_specs_list == []
    assert totaling.module_spec is None
    assert esl.module_spec is None


def test_hydrate_experiment_climate_module_produces_module_spec():
    skeleton = make_skeleton(climate_module="fair-temperature")
    schemas = {"fair-temperature": make_schema(name="fair-temperature")}
    climate, _, _, _ = hydrate_experiment(skeleton, schemas)

    assert climate.module_spec is not None
    assert climate.module_spec.module_name == "fair-temperature"


def test_hydrate_experiment_totaling_module_produces_module_spec():
    schemas = {"facts-total": make_schema("facts-total")}
    skeleton = make_skeleton(totaling_module="facts-total", sealevel_modules=[])

    _, _, totaling, _ = hydrate_experiment(skeleton, schemas)

    assert totaling.module_spec is not None
    assert totaling.module_spec.module_name == "facts-total"


def test_hydrate_experiment_esl_module_produces_module_spec():
    skeleton = make_skeleton(
        extremesealevel_module="extremesealevel-pointsoverthreshold"
    )
    schemas = {
        "extremesealevel-pointsoverthreshold": make_schema(
            "extremesealevel-pointsoverthreshold"
        )
    }

    _, _, _, esl = hydrate_experiment(skeleton, schemas)

    assert esl.module_spec is not None
    assert esl.module_spec.module_name == "extremesealevel-pointsoverthreshold"


# @patch(
#    "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
# )
# def test_hydrate_sealevel_step_merges_climate_data_using_module_specific_input_key(
#     mock_load,
# ):
#     """Modules with a non-standard climate input name (e.g. input-data-file) get the
#     climate file path merged under the correct key, not climate_data_file."""
#     schema = ModuleSchema(
#         module_name="emulandice-ais",
#         container_image="test/image:latest",
#         arguments={
#             "inputs": [
#                 {
#                     "name": "input-data-file",
#                     "source": "module_inputs.inputs.input_data_file",
#                     "mount": {"volume": "output", "container_path": "/mnt/out"},
#                 }
#             ],
#             "options": [],
#             "outputs": {},
#             "top_level": [],
#         },
#         volumes={
#             "output": {
#                 "host_path": "module_inputs.output_paths.output_dir",
#                 "container_path": "/mnt/out",
#             }
#         },
#         uses_climate_file=True,
#     )
#     mock_load.side_effect = [schema]
#     skeleton = make_skeleton(sealevel_modules=["emulandice-ais"])

#     step = hydrate_sealevel_step(
#         skeleton,
#         climate_files={"emulandice-ais": "fair-temperature/climate.nc"},
#     )

#     inputs = step.module_specs_list[0].to_dict().get("inputs", {})
#     assert (
#         inputs.get("input_data_file", {}).get("value") == "fair-temperature/climate.nc"
#     )
#     assert "climate_data_file" not in inputs


# @patch(
#     "facts_experiment_builder.application.setup_experiment.load_module_schema_by_name"
# )
# def test_hydrate_sealevel_step_skips_merge_for_modules_without_climate_file(mock_load):
#     schema = (make_schema("bamber19-icesheets", uses_climate_file=False),)

#     skeleton = make_skeleton(
#         sealevel_modules=["bamber19-icesheets"],
#         climate_data="/path/to/climate.nc",
#     )

#     step = hydrate_sealevel_step(skeleton, schema=schema)

#     spec = step.module_specs_list[0]
#     inputs = spec.to_dict().get("inputs", {})
#     assert "climate_data_file" not in inputs


# --- top_level_context threading ---


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


# TODO : add test similar to this in test_module_schema and test that incorrect things fail etc.
def test_hydrate_experiment_prefills_climate_file_from_climate_module():
    """Sealevel module gets climate-data-file = '{climate_module}/{filename}' derived
    from climate_output_type on the sealevel schema."""

    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["bamber19-icesheets"],
    )

    schemas = {
        "fair-temperature": make_schema(
            "fair-temperature",
            arguments={
                "outputs": {
                    "files": [
                        {
                            "name": "output-climate-file",
                            "type": "file",
                            "source": "module_inputs.output.output_0",
                            "output_type": "global",
                            "filename": "climate.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                    ]
                }
            },
        ),
        "bamber19-icesheets": make_schema(
            "bamber19-icesheets",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-climate-file",
                    }
                ]
            },
        ),
    }

    _, sealevel, _, _ = hydrate_experiment(skeleton, schemas)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value")
        == "fair-temperature/climate.nc"
    )


def test_hydrate_experiment_doesnt_return_wrong_climate_file():
    """Sealevel module gets climate-data-file = '{climate_module}/{filename}' derived
    from climate_output_type on the sealevel schema."""

    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["bamber19-icesheets"],
    )

    schemas = {
        "fair-temperature": make_schema(
            "fair-temperature",
            arguments={
                "outputs": {
                    "files": [
                        {
                            "name": "output-climate-file",
                            "type": "file",
                            "source": "module_inputs.output.output_0",
                            "output_type": "global",
                            "filename": "climate.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                    ]
                }
            },
        ),
        "bamber19-icesheets": make_schema(
            "bamber19-icesheets",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-climate-file",
                    }
                ]
            },
        ),
    }

    _, sealevel, _, _ = hydrate_experiment(skeleton, schemas)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value") != "fair-temperature/gsat.nc"
    )


def test_hydrate_experiment_prefills_climate_file_from_climate_module_2():
    """Sealevel module gets climate-data-file = '{climate_module}/{filename}' derived
    from climate_output_type on the sealevel schema."""

    skeleton = make_skeleton(
        climate_module="fair2-climate",
        sealevel_modules=["bamber19-icesheets"],
    )

    schemas = {
        "fair2-climate": make_schema(
            "fair2-climate",
            arguments={
                "outputs": {
                    "files": [
                        {
                            "name": "output-climate-file",
                            "type": "file",
                            "source": "module_inputs.output.output_0",
                            "output_type": "global",
                            "filename": "climate.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                    ]
                }
            },
        ),
        "bamber19-icesheets": make_schema(
            "bamber19-icesheets",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-climate-file",
                    }
                ]
            },
        ),
    }

    _, sealevel, _, _ = hydrate_experiment(skeleton, schemas)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value") == "fair2-climate/climate.nc"
    )


# def test_hydrate_experiment_matches_correct_climate_file_with_expected_by_sealevel_module():
#     skeleton = make_skeleton(
#         climate_module="fair-temperature",
#         sealevel_modules=["fittedismip-gris", "emulandice2-ais"]
#     )
#     schemas = {
#         "fair-temperature": make_schema("fair_temperature"),
#         "fittedismip-gris": make_schema("fittedismip-gris", uses_climate_file=True),
#         "emulandice2-ais": make_schema("emulandice2-ais", uses_climate_file=True)
#     }
#     _, sealevel,_,_ = hydrate_experiment(skeleton, schemas)
#     print('fitted ismip gris step stuff: ', sealevel.module_specs_list[0])


def test_hydrate_experiment_prefills_correct_file_for_different_climate_module():
    """When the climate module changes, the prefilled path prefix changes accordingly."""

    skeleton = make_skeleton(
        climate_module="fair2-climate",
        sealevel_modules=["bamber19-icesheets"],
    )
    schemas = {
        "fair2-climate": make_schema(
            "fair2-climate",
            arguments={
                "outputs": {
                    "files": [
                        {
                            "name": "output-climate-file",
                            "type": "file",
                            "source": "module_inputs.output.output_0",
                            "output_type": "global",
                            "filename": "climate.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                    ]
                }
            },
        ),
        "bamber19-icesheets": make_schema(
            "bamber19-icesheets",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-climate-file",
                    }
                ]
            },
        ),
    }

    _, sealevel, _, _ = hydrate_experiment(skeleton, schemas)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value") == "fair2-climate/climate.nc"
    )


def test_hydrate_experiment_prefills_gsat_file_for_sealevel_module_expecting_gsat():
    """Sealevel module with climate_output_type='output-gsat-file' gets the gsat output."""

    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["emulandice-ais"],
    )
    schemas = {
        "fair-temperature": make_schema(
            "fair-temperature",
            arguments={
                "outputs": {
                    "files": [
                        {
                            "name": "output-climate-file",
                            "type": "file",
                            "source": "module_inputs.output.output_0",
                            "output_type": "global",
                            "filename": "climate.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                        {
                            "name": "output-gsat-file",
                            "type": "file",
                            "source": "module_inpputs.output.output_1",
                            "output_type": "global",
                            "filename": "gsat.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                    ]
                }
            },
        ),
        "emulandice-ais": make_schema(
            "emulandice-ais",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-gsat-file",
                    }
                ]
            },
        ),
    }

    _, sealevel, _, _ = hydrate_experiment(skeleton, schemas=schemas)

    inputs = sealevel.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value") == "fair-temperature/gsat.nc"
    )


def test_hydrate_experiment_prefills_per_module_independently():
    """Two sealevel modules with different climate_output_type each get the right file."""

    skeleton = make_skeleton(
        climate_module="fair-temperature",
        sealevel_modules=["emulandice-ais", "fittedismip-gris"],
    )
    schemas = {
        "fair-temperature": make_schema(
            "fair-temperature",
            arguments={
                "outputs": {
                    "files": [
                        {
                            "name": "output-climate-file",
                            "type": "file",
                            "source": "module_inputs.output.output_0",
                            "output_type": "global",
                            "filename": "climate.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                        {
                            "name": "output-gsat-file",
                            "type": "file",
                            "source": "module_inpputs.output.output_1",
                            "output_type": "global",
                            "filename": "gsat.nc",
                            "help": "help",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        },
                    ]
                }
            },
        ),
        "emulandice-ais": make_schema(
            "emulandice-ais",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-gsat-file",
                    }
                ]
            },
        ),
        "fittedismip-gris": make_schema(
            "fittedismip-gris",
            uses_climate_file=True,
            arguments={
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "output-climate-file",
                    }
                ]
            },
        ),
    }

    _, sealevel, _, _ = hydrate_experiment(skeleton, schemas)

    gsat_input = sealevel.module_specs_list[0].inputs["climate_data_file"]["value"]
    print("should be gsat: ", gsat_input)
    assert gsat_input == "fair-temperature/gsat.nc"

    climate_input = sealevel.module_specs_list[1].inputs["climate_data_file"]["value"]
    assert climate_input == "fair-temperature/climate.nc"
