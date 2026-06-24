"""Tests for the module_adapter module."""

from unittest.mock import MagicMock, patch

from facts_experiment_builder.adapters.module_adapter import (
    create_module_service_spec_from_metadata,
)


def test_create_module_service_spec_accepts_path_experiment_dir(tmp_path):
    """experiment_dir must be a Path; regression test for the str annotation bug."""
    with (
        patch(
            "facts_experiment_builder.adapters.module_adapter.load_experiment_metadata",
            return_value={"temperature_module": "fair-temperature"},
        ) as mock_load,
        patch(
            "facts_experiment_builder.adapters.module_adapter.build_module_service_spec",
            return_value=MagicMock(),
        ),
    ):
        create_module_service_spec_from_metadata(
            tmp_path,
            module_name="fair-temperature",
            module_type="temperature_module",
            metadata=None,  # forces the load branch that constructs path from experiment_dir
        )
        mock_load.assert_called_once_with(tmp_path / "experiment-config.yaml")
