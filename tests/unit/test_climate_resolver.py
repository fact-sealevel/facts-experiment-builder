"""Tests for resolve_climate_file."""

import pytest
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.climate_resolver import resolve_climate_file


def _climate_schema(module_name: str) -> ModuleSchema:
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


def test_resolves_climate_file_for_fair_temperature():
    schema = _climate_schema("fair-temperature")
    assert (
        resolve_climate_file(schema, "output-climate-file")
        == "fair-temperature/climate.nc"
    )


def test_resolves_gsat_file_for_fair_temperature():
    schema = _climate_schema("fair-temperature")
    assert (
        resolve_climate_file(schema, "output-gsat-file") == "fair-temperature/gsat.nc"
    )


def test_resolves_climate_file_for_different_climate_module():
    schema = _climate_schema("fair2-climate")
    assert (
        resolve_climate_file(schema, "output-climate-file")
        == "fair2-climate/climate.nc"
    )


def test_resolves_gsat_file_for_different_climate_module():
    schema = _climate_schema("fair2-climate")
    assert resolve_climate_file(schema, "output-gsat-file") == "fair2-climate/gsat.nc"


def test_raises_for_unknown_output_type():
    schema = _climate_schema("fair-temperature")
    with pytest.raises(ValueError, match="output-unknown-file"):
        resolve_climate_file(schema, "output-unknown-file")


def test_error_message_lists_available_outputs():
    schema = _climate_schema("fair-temperature")
    with pytest.raises(ValueError, match="output-climate-file"):
        resolve_climate_file(schema, "output-unknown-file")
