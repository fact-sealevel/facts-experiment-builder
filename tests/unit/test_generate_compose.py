"""Tests for the generate_compose module."""

import pytest
from facts_experiment_builder.application import generate_compose
from unittest.mock import patch
from pathlib import Path


def test_module_requires_climate_file_false_when_key_false(tmp_path: Path):
    """Test _module_requires_climate_file function."""
    module_yaml = tmp_path / "test_module_module.yaml"
    module_yaml.write_text("climate_file_required: false \n")

    with patch(
        "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
        return_value=module_yaml,
    ):
        result = generate_compose._module_requires_climate_file("test-module")
        assert not result


def test_module_requires_climate_file_true_when_key_true(
    climate_required_true_module_yaml, patched_find_module_yaml_path
):
    """Test _module_requires_climate_file function."""
    result = generate_compose._module_requires_climate_file("test-module")
    assert result


def _write_module_yaml_with_input(tmp_path: Path, input_name: str) -> Path:
    """Write a minimal module YAML with uses_climate_file: true and a named input on the output volume."""
    source_key = input_name.replace("-", "_")
    yaml_path = tmp_path / "test_module_module.yaml"
    yaml_path.write_text(
        f"uses_climate_file: true\n"
        f"volumes:\n"
        f"  output:\n"
        f"    host_path: module_inputs.output_paths.output_dir\n"
        f"    container_path: /mnt/out\n"
        f"arguments:\n"
        f"  inputs:\n"
        f"    - name: {input_name}\n"
        f"      source: module_inputs.inputs.{source_key}\n"
        f"      mount:\n"
        f"        volume: output\n"
        f"        container_path: /mnt/out\n"
    )
    return yaml_path


def test_validate_climate_file_inputs_passes_with_standard_key(tmp_path: Path):
    """Validation succeeds when the module's climate input key is provided in metadata."""
    yaml_path = _write_module_yaml_with_input(tmp_path, "climate-data-file")
    metadata = {
        "test-module": {"inputs": {"climate_data_file": "fair-temperature/climate.nc"}}
    }

    with patch(
        "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
        return_value=yaml_path,
    ):
        generate_compose._validate_climate_file_inputs(
            metadata, ["test-module"], tmp_path
        )


def test_validate_climate_file_inputs_passes_with_nonstandard_key(tmp_path: Path):
    """Validation succeeds when the module uses a non-standard climate input name."""
    yaml_path = _write_module_yaml_with_input(tmp_path, "input-data-file")
    metadata = {
        "test-module": {"inputs": {"input_data_file": "fair-temperature/climate.nc"}}
    }

    with patch(
        "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
        return_value=yaml_path,
    ):
        generate_compose._validate_climate_file_inputs(
            metadata, ["test-module"], tmp_path
        )


def test_validate_climate_file_inputs_raises_when_nonstandard_key_missing(
    tmp_path: Path,
):
    """Validation raises when a module with a non-standard climate input name has no value."""
    yaml_path = _write_module_yaml_with_input(tmp_path, "input-data-file")
    metadata = {"test-module": {"inputs": {}}}

    with patch(
        "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
        return_value=yaml_path,
    ):
        with pytest.raises(ValueError, match="test-module"):
            generate_compose._validate_climate_file_inputs(
                metadata, ["test-module"], tmp_path
            )
