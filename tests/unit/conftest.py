"""Shared fixtures for unit tests."""

import logging
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True)
def reset_feb_logger():
    """Reset facts_experiment_builder logger state between tests.

    _configure_feb_logging() (called by CLI tests) sets propagate=False on the
    facts_experiment_builder logger. This persists across tests in the same session
    and prevents caplog from capturing log records in later tests.
    """
    yield
    logger = logging.getLogger("facts_experiment_builder")
    logger.propagate = True
    logger.handlers.clear()


@pytest.fixture
def climate_required_true_module_yaml(tmp_path) -> Path:
    """Module YAML file with climate_file_required: true."""
    yaml_path = tmp_path / "test_module_module.yaml"
    yaml_path.write_text("uses_climate_file: true\n")
    return yaml_path


@pytest.fixture
def patched_find_module_yaml_path(climate_required_true_module_yaml: Path):
    """Patches find_module_yaml_path to return climate_required_module_yaml."""
    with patch(
        "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
        return_value=climate_required_true_module_yaml,
    ) as mock:
        yield mock
