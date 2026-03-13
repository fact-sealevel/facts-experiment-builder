"""Minimal pytest suite for setup_new_experiment_cli."""


from click.testing import CliRunner

from facts_experiment_builder.cli.setup_new_experiment_cli import main
from facts_experiment_builder.core.registry import ModuleRegistry
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list,
    validate_module_names,
)

import pytest

runner = CliRunner()


def test_cli_help_exits_zero():
    """--help runs and exits with 0."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "experiment-name" in result.output
    assert "temperature-module" in result.output
    assert "sealevel-modules" in result.output
    assert "framework-module" in result.output


def test_cli_fails_without_required_args():
    """Invoking without required options exits non-zero."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert (
        "experiment-name" in result.output
        or "Missing" in result.output
        or "Error" in result.output
    )

def test_setup_new_experiment_fails_with_invalid_module_name():
    
    result = runner.invoke(main,
    [
        "--experiment-name",
        "test-exp",
        "--temperature-module",
        "fair-temperature",
        "--sealevel-modules",
        "ipccar5-icesheets,ipccar5-glaciers,invalid-module-name",
    ])
    assert result.exit_code != 0
    #assert "Invalid module name(s): invalid-module-name" in result.output



