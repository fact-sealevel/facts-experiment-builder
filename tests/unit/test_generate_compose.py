"""Tests for the generate_compose module."""

import pytest

from facts_experiment_builder.application.generate_compose import (
    _SUCCESS,
    _log_success,
    check_metadata_has_required_fields,
)
from facts_experiment_builder.application.prepare_plan import (
    _validate_climate_file_inputs,
    check_module_schemas_present,
)
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema


def _make_climate_schema(input_name: str) -> ModuleSchema:
    source_key = input_name.replace("-", "_")
    return ModuleSchema(
        module_name="test-module",
        container_image="img:tag",
        uses_climate_file=True,
        arguments=ArgumentsSpec.model_validate(
            {
                "inputs": [
                    {
                        "name": input_name,
                        "type": "str",
                        "source": f"module_inputs.inputs.{source_key}",
                        "climate_step_output": "output-climate-file",
                        "mount": {"volume": "output", "container_path": "/mnt/out"},
                    }
                ]
            }
        ),
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
    )


def test_validate_climate_file_inputs_passes_with_standard_key():
    """Validation succeeds when the module's climate input key is provided in metadata."""
    schema = _make_climate_schema("climate-data-file")
    metadata = {
        "test-module": {"inputs": {"climate-data-file": "fair-temperature/climate.nc"}}
    }
    _validate_climate_file_inputs(metadata, ["test-module"], {"test-module": schema})


def test_validate_climate_file_inputs_passes_with_nonstandard_key():
    """Validation succeeds when the module uses a non-standard climate input name."""
    schema = _make_climate_schema("input-data-file")
    metadata = {
        "test-module": {"inputs": {"input-data-file": "fair-temperature/climate.nc"}}
    }
    _validate_climate_file_inputs(metadata, ["test-module"], {"test-module": schema})


def test_validate_climate_file_inputs_raises_when_nonstandard_key_missing():
    """Validation raises when a module with a non-standard climate input name has no value."""
    schema = _make_climate_schema("input-data-file")
    metadata = {"test-module": {"inputs": {}}}
    with pytest.raises(ValueError, match="test-module"):
        _validate_climate_file_inputs(
            metadata, ["test-module"], {"test-module": schema}
        )


def test_check_metadata_has_required_fields():
    required_fields = {
        "experiment-name": "my-test-exp",
        "pipeline-id": "abc123",
        "nsamps": 100,
    }
    metadata_complete = {
        "experiment-name": "my-test-exp",
        "pipeline-id": "abc123",
        "nsamps": 100,
        "scenario": "ssp585",
    }
    metadata_incomplete = {
        "pipeline-id": "abc123",
        "nsamps": 100,
        "experiment-name": None,
    }
    check_metadata_has_required_fields(metadata_complete, required_fields)

    with pytest.raises(ValueError, match="experiment-name"):
        check_metadata_has_required_fields(
            metadata_incomplete, required_fields=["experiment-name"]
        )


def test_check_module_schemas_present_raises_when_key_missing():
    with pytest.raises(ValueError, match="module_schemas"):
        check_module_schemas_present(None, ["fair-temperature"])


def test_check_module_schemas_present_raises_when_module_missing():
    module_schemas = {"fair-temperature": {}}
    with pytest.raises(ValueError, match="tlm-sterodynamics"):
        check_module_schemas_present(
            module_schemas, ["fair-temperature", "tlm-sterodynamics"]
        )


def test_check_module_schemas_present_passes_when_all_present():
    module_schemas = {"fair-temperature": {}}
    check_module_schemas_present(module_schemas, ["fair-temperature"])  # no raise


def test_log_success_emits_at_correct_level(caplog):
    with caplog.at_level(
        _SUCCESS, logger="facts_experiment_builder.application.generate_compose"
    ):
        _log_success("Created %s module", "my-module")

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == _SUCCESS
    assert caplog.records[0].getMessage() == "Created my-module module"
