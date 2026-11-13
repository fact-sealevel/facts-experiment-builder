"""Tests for LoadedExperimentConfig."""

import pytest

from facts_experiment_builder.core.experiment.loaded_config import (
    _REQUIRED_FIELDS,
    LoadedExperimentConfig,
)
from tests.unit.helpers import make_config_raw


def test_module_names_returns_all_modules_in_step_order():
    config = LoadedExperimentConfig.from_dict(
        make_config_raw(
            climate_module="fair-temperature",
            sealevel_modules=["bamber19-icesheets", "tlm-sterodynamics"],
            framework_modules=["facts-total"],
            esl_modules=["extremesealevel-pointsoverthreshold"],
        )
    )
    assert config.module_names == [
        "fair-temperature",
        "bamber19-icesheets",
        "tlm-sterodynamics",
        "facts-total",
        "extremesealevel-pointsoverthreshold",
    ]


@pytest.mark.parametrize("climate", ["NONE", "none"])
def test_module_names_excludes_none_climate_module(climate):
    config = LoadedExperimentConfig.from_dict(
        make_config_raw(climate_module=climate, sealevel_modules=["tlm-sterodynamics"])
    )
    assert config.module_names == ["tlm-sterodynamics"]


def test_optional_fields_default_when_missing():
    config = LoadedExperimentConfig.from_dict(make_config_raw())
    assert config.module_names == []
    assert config.workflows == {}
    assert config.module_sections == {}
    assert config.module_schemas is None
    assert config.projection_scale is None
    assert config.location_file is None


def test_non_string_manifest_entries_are_dropped():
    config = LoadedExperimentConfig.from_dict(
        make_config_raw(sealevel_modules=["a", None, 3])
    )
    assert config.sealevel_modules == ["a"]


def test_hyphenated_keys_map_to_fields():
    config = LoadedExperimentConfig.from_dict(
        make_config_raw(
            **{"location-file": "location.lst", "experiment-specific-input-data": []}
        )
    )
    assert config.pipeline_id == "abc123"
    assert config.location_file == "location.lst"
    assert config.module_specific_input_data == "/in/module"
    assert config.shared_input_data == "/in/shared"
    assert config.compose_output_data_location == "/out/compose"
    assert config.apptainer_output_data_location == "/out/apptainer"
    assert config.output_data_location is None
    assert config.experiment_specific_input_data == []


def test_module_sections_hold_only_manifest_modules():
    raw = make_config_raw(
        **{
            "climate_module": "fair-temperature",
            "sealevel_modules": ["tlm-sterodynamics"],
            "fair-temperature": {"inputs": {}},
            "tlm-sterodynamics": {"inputs": {"a": 1}},
            "workflows": {"wf1": "tlm-sterodynamics"},
        }
    )
    config = LoadedExperimentConfig.from_dict(raw)
    assert config.module_sections == {
        "fair-temperature": {"inputs": {}},
        "tlm-sterodynamics": {"inputs": {"a": 1}},
    }
    assert config.raw is raw


@pytest.mark.parametrize("raw", [None, [], "text"])
def test_non_mapping_raises_value_error(raw):
    with pytest.raises(ValueError, match="not a mapping"):
        LoadedExperimentConfig.from_dict(raw)


@pytest.mark.parametrize("key", sorted(_REQUIRED_FIELDS.values()))
def test_missing_required_key_raises(key):
    raw = make_config_raw()
    del raw[key]
    with pytest.raises(ValueError, match=key):
        LoadedExperimentConfig.from_dict(raw)


def test_null_required_value_raises():
    with pytest.raises(ValueError, match="nsamps"):
        LoadedExperimentConfig.from_dict(make_config_raw(nsamps=None))


def test_all_missing_required_keys_are_listed():
    with pytest.raises(ValueError) as exc:
        LoadedExperimentConfig.from_dict({})
    for key in _REQUIRED_FIELDS.values():
        assert key in str(exc.value)


@pytest.mark.parametrize("value", ["100", 100.0, True])
def test_non_integer_int_field_raises(value):
    with pytest.raises(ValueError, match="must be integers: nsamps"):
        LoadedExperimentConfig.from_dict(make_config_raw(nsamps=value))
