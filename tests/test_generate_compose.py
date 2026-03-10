"""Tests for the generate_compose module."""

from facts_experiment_builder.application import generate_compose
from unittest.mock import patch
from pathlib import Path


def test_module_requires_climate_file_false_when_key_false(tmp_path: Path):
    """Test _module_requires_climate_file function."""
    module_yaml = tmp_path / "test_module_module.yaml"
    module_yaml.write_text("climate_file_required: false \n")

    with (
        patch(
            "facts_experiment_builder.application.generate_compose.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
            return_value=module_yaml,
        ),
    ):
        result = generate_compose._module_requires_climate_file("test-module", tmp_path)
        assert not result


def test_module_requires_climate_file_true_when_key_true(tmp_path: Path):
    """Test _module_requires_climate_file function."""
    module_yaml = tmp_path / "test_module_module.yaml"
    module_yaml.write_text("climate_file_required: true \n")

    with (
        patch(
            "facts_experiment_builder.application.generate_compose.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
            return_value=module_yaml,
        ),
    ):
        result = generate_compose._module_requires_climate_file("test-module", tmp_path)
        assert result
