"""Unit tests for cli/utils.py."""

import pytest
import click
from unittest.mock import patch

from facts_experiment_builder.cli.utils import check_registry_accessible


def test_check_registry_raises_usage_error_when_registry_missing():
    with patch(
        "facts_experiment_builder.cli.utils.ModuleRegistry.default",
        side_effect=FileNotFoundError("registry not found"),
    ):
        with pytest.raises(click.UsageError, match="registry not found"):
            check_registry_accessible()


def test_check_registry_returns_registry_when_found(tmp_path):
    from facts_experiment_builder.core.registry import ModuleRegistry

    fake_registry = ModuleRegistry(tmp_path)
    with patch(
        "facts_experiment_builder.cli.utils.ModuleRegistry.default",
        return_value=fake_registry,
    ):
        result = check_registry_accessible()
        assert result is fake_registry
