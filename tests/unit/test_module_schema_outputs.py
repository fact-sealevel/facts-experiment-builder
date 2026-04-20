"""Tests for ModuleSchema output/input helper methods and ModuleExperimentSpec output handling."""

import pytest
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FILE_OUTPUT_SPEC = {
    "name": "output-gslr-file",
    "type": "file",
    "source": "module_inputs.outputs.output_gslr_file",
    "filename": "output-gslr.nc",
    "output_type": "global",
    "mount": {"volume": "output", "container_path": "/mnt/out"},
}

OTHER_OUTPUT_SPEC = {
    "name": "output-glacier-dir",
    "type": "str",
    "source": "module_inputs.outputs.output_glacier_dir",
    "mount": {"volume": "output", "container_path": "/mnt/out"},
    "optional": True,
}


def _schema(outputs):
    return ModuleSchema(
        module_name="test-module",
        container_image="img:tag",
        arguments={"inputs": [], "options": [], "outputs": outputs},
        volumes={},
    )


# ---------------------------------------------------------------------------
# get_file_outputs
# ---------------------------------------------------------------------------


def test_get_file_outputs_returns_files_section():
    schema = _schema({"files": [FILE_OUTPUT_SPEC], "other": [OTHER_OUTPUT_SPEC]})
    result = schema.get_file_outputs()
    assert len(result) == 1
    assert result[0]["name"] == "output-gslr-file"


def test_get_file_outputs_missing_files_key():
    schema = _schema({"other": [OTHER_OUTPUT_SPEC]})
    assert schema.get_file_outputs() == []


def test_get_file_outputs_empty_outputs():
    schema = _schema({})
    assert schema.get_file_outputs() == []


# ---------------------------------------------------------------------------
# get_other_outputs
# ---------------------------------------------------------------------------


def test_get_other_outputs_returns_other_section():
    schema = _schema({"files": [FILE_OUTPUT_SPEC], "other": [OTHER_OUTPUT_SPEC]})
    result = schema.get_other_outputs()
    assert len(result) == 1
    assert result[0]["name"] == "output-glacier-dir"


def test_get_other_outputs_missing_other_key():
    schema = _schema({"files": [FILE_OUTPUT_SPEC]})
    assert schema.get_other_outputs() == []


# ---------------------------------------------------------------------------
# get_outputs_list
# ---------------------------------------------------------------------------


def test_get_outputs_list_returns_all():
    schema = _schema({"files": [FILE_OUTPUT_SPEC], "other": [OTHER_OUTPUT_SPEC]})
    result = schema.get_outputs_list()
    assert len(result) == 2
    names = {o["name"] for o in result}
    assert names == {"output-gslr-file", "output-glacier-dir"}


def test_get_outputs_list_empty_outputs():
    schema = _schema({})
    assert schema.get_outputs_list() == []


# ---------------------------------------------------------------------------
# _output_volume_key and get_output_volume_input_keys
# ---------------------------------------------------------------------------

OUTPUT_VOLUME = {
    "output": {
        "host_path": "module_inputs.output_paths.output_dir",
        "container_path": "/mnt/out",
    }
}
OTHER_VOLUMES = {
    "module_specific_input": {
        "host_path": "module_inputs.input_paths.module_specific_input_dir",
        "container_path": "/mnt/module_specific_in",
    },
    "shared_input": {
        "host_path": "module_inputs.input_paths.shared_input_dir",
        "container_path": "/mnt/shared_in",
    },
}


def _schema_with_inputs(inputs, volumes=None):
    return ModuleSchema(
        module_name="test-module",
        container_image="img:tag",
        arguments={"inputs": inputs, "options": [], "outputs": {}},
        volumes=volumes if volumes is not None else {**OUTPUT_VOLUME, **OTHER_VOLUMES},
    )


def test_output_volume_key_returns_correct_key():
    schema = _schema_with_inputs([])
    assert schema._output_volume_key() == "output"


def test_output_volume_key_returns_none_when_no_output_volume():
    schema = _schema_with_inputs([], volumes=OTHER_VOLUMES)
    assert schema._output_volume_key() is None


def test_output_volume_key_returns_none_for_empty_volumes():
    schema = _schema_with_inputs([], volumes={})
    assert schema._output_volume_key() is None


def test_get_output_volume_input_keys_returns_name_and_source_key():
    """Both the YAML arg name and the source-derived snake_case key are returned."""
    inputs = [
        {
            "name": "input-data-file",
            "source": "module_inputs.inputs.input_data_file",
            "mount": {"volume": "output", "container_path": "/mnt/out"},
        }
    ]
    schema = _schema_with_inputs(inputs)
    keys = schema.get_output_volume_input_keys()
    assert "input-data-file" in keys
    assert "input_data_file" in keys


def test_get_output_volume_input_keys_excludes_non_output_volume_inputs():
    inputs = [
        {
            "name": "some-file",
            "source": "module_inputs.inputs.some_file",
            "mount": {
                "volume": "module_specific_input",
                "container_path": "/mnt/module_specific_in",
            },
        }
    ]
    schema = _schema_with_inputs(inputs)
    assert schema.get_output_volume_input_keys() == set()


def test_get_output_volume_input_keys_handles_multiple_inputs():
    """Only output-volume inputs are included; other inputs are excluded."""
    inputs = [
        {
            "name": "climate-data-file",
            "source": "module_inputs.inputs.climate_data_file",
            "mount": {"volume": "output", "container_path": "/mnt/out"},
        },
        {
            "name": "location-file",
            "source": "module_inputs.inputs.location_file",
            "mount": {"volume": "shared_input", "container_path": "/mnt/shared_in"},
        },
    ]
    schema = _schema_with_inputs(inputs)
    keys = schema.get_output_volume_input_keys()
    assert "climate-data-file" in keys
    assert "climate_data_file" in keys
    assert "location-file" not in keys
    assert "location_file" not in keys


def test_get_output_volume_input_keys_empty_when_no_output_volume():
    """Returns empty set when the module has no output volume defined."""
    inputs = [
        {
            "name": "input-data-file",
            "source": "module_inputs.inputs.input_data_file",
            "mount": {"volume": "output", "container_path": "/mnt/out"},
        }
    ]
    schema = _schema_with_inputs(inputs, volumes=OTHER_VOLUMES)
    assert schema.get_output_volume_input_keys() == set()


# ---------------------------------------------------------------------------
# ModuleExperimentSpec.from_module_schema — output handling
# ---------------------------------------------------------------------------


def test_from_module_schema_other_output_stored_without_output_type():
    """A type: str output should be stored with only a 'value' key (no output_type)."""
    schema = _schema({"files": [FILE_OUTPUT_SPEC], "other": [OTHER_OUTPUT_SPEC]})
    spec = ModuleExperimentSpec.from_module_schema(schema)
    dir_output = spec.outputs.get("output-glacier-dir")
    assert dir_output is not None
    assert dir_output["value"] == "test-module"
    assert "output_type" not in dir_output


def test_from_module_schema_file_output_stored_with_output_type():
    """A type: file output should be stored with value and output_type."""
    schema = _schema({"files": [FILE_OUTPUT_SPEC]})
    spec = ModuleExperimentSpec.from_module_schema(schema)
    file_output = spec.outputs.get("output-gslr-file")
    assert file_output is not None
    assert file_output["value"] == "test-module/output-gslr.nc"
    assert file_output["output_type"] == "global"


def test_from_module_schema_raises_for_file_output_missing_filename():
    """A file output without 'filename' should raise ValueError."""
    bad_spec = {**FILE_OUTPUT_SPEC}
    del bad_spec["filename"]
    schema = _schema({"files": [bad_spec]})
    with pytest.raises(ValueError, match="missing"):
        ModuleExperimentSpec.from_module_schema(schema)


def test_from_module_schema_raises_for_file_output_missing_output_type():
    """A file output without 'output_type' should raise ValueError."""
    bad_spec = {**FILE_OUTPUT_SPEC}
    del bad_spec["output_type"]
    schema = _schema({"files": [bad_spec]})
    with pytest.raises(ValueError, match="output_type"):
        ModuleExperimentSpec.from_module_schema(schema)


# ---------------------------------------------------------------------------
# ModuleExperimentSpec — fingerprint_params handling
# ---------------------------------------------------------------------------

FP_SPEC_MODULE_SPECIFIC = {
    "name": "fprint-gis-file",
    "type": "str",
    "source": "module_inputs.fingerprint_params.fprint_gis_file",
    "help": "File containing GIS fingerprint data",
    "mount": {"volume": "shared_input", "container_path": "/mnt/shared_in"},
}

FP_SPEC_TOP_LEVEL = {
    "name": "location-file",
    "type": "str",
    "source": "metadata.location-file",
    "help": "Location file",
    "mount": {"volume": "shared_input", "container_path": "/mnt/shared_in"},
}


def _schema_with_fp(fingerprint_params):
    return ModuleSchema(
        module_name="test-module",
        container_image="img:tag",
        arguments={
            "inputs": [],
            "options": [],
            "outputs": {"files": [FILE_OUTPUT_SPEC]},
            "fingerprint_params": fingerprint_params,
        },
        volumes={},
    )


def test_from_module_schema_includes_module_specific_fingerprint_params():
    """Module-specific fingerprint params (source: module_inputs.fingerprint_params.*) appear in the spec."""
    schema = _schema_with_fp([FP_SPEC_MODULE_SPECIFIC])
    spec = ModuleExperimentSpec.from_module_schema(schema)
    assert "fprint_gis_file" in spec.fingerprint_params
    entry = spec.fingerprint_params["fprint_gis_file"]
    assert entry.get("clue") == "File containing GIS fingerprint data"


def test_from_module_schema_excludes_top_level_fingerprint_params():
    """Top-level fingerprint params (source: metadata.*) are NOT added to the spec — they come from top-level metadata."""
    schema = _schema_with_fp([FP_SPEC_TOP_LEVEL])
    spec = ModuleExperimentSpec.from_module_schema(schema)
    assert spec.fingerprint_params == {}


def test_from_module_schema_fingerprint_params_omitted_from_to_dict_when_empty():
    """to_dict() omits the fingerprint_params key when there are none."""
    schema = _schema_with_fp([FP_SPEC_TOP_LEVEL])
    spec = ModuleExperimentSpec.from_module_schema(schema)
    assert "fingerprint_params" not in spec.to_dict()


def test_from_module_schema_fingerprint_params_present_in_to_dict_when_populated():
    """to_dict() includes fingerprint_params when the spec has them."""
    schema = _schema_with_fp([FP_SPEC_MODULE_SPECIFIC])
    spec = ModuleExperimentSpec.from_module_schema(schema)
    d = spec.to_dict()
    assert "fingerprint_params" in d
    assert "fprint_gis_file" in d["fingerprint_params"]


def test_from_dict_round_trips_fingerprint_params():
    """from_dict() parses fingerprint_params so they survive a round-trip."""
    raw = {
        "inputs": {},
        "options": {},
        "outputs": {},
        "fingerprint_params": {
            "fprint_gis_file": {"clue": "GIS fp", "value": "fprint_gis.nc"}
        },
        "image": "img:tag",
    }
    spec = ModuleExperimentSpec.from_dict("test-module", raw)
    assert spec.fingerprint_params.get("fprint_gis_file") == {
        "clue": "GIS fp",
        "value": "fprint_gis.nc",
    }
    assert (
        spec.to_dict()["fingerprint_params"]["fprint_gis_file"]["value"]
        == "fprint_gis.nc"
    )
