"""Minimal pytest suite for setup_new_experiment_cli."""

from click.testing import CliRunner
import click
from facts_experiment_builder.cli.setup_new_experiment_cli import (
    main,
    _validate_modules_list_experiment,
    _validate_modules_list_workflow,
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
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--temperature-module",
            "fair-temperature",
            "--sealevel-modules",
            "ipccar5-icesheets,ipccar5-glaciers,invalid-module-name",
        ],
    )
    assert result.exit_code != 0
    # assert "Invalid module name(s): invalid-module-name" in result.output


def test_validate_modules_list_experiment_passes_for_valid():
    valid_module_names = ["fair-temperature", "ipccar5-icesheets", "ipccar5-glaciers"]
    _validate_modules_list_experiment(valid_module_names)


def test_validate_modules_list_experiment_fails_for_invalid():
    invalid_module_names = ["invalid-module-name", "invalid-module-name-2"]
    with pytest.raises(click.UsageError):
        _validate_modules_list_experiment(invalid_module_names)


def test_validate_modules_list_workflow_passes_for_valid():
    experiment_modules_list = [
        "ipccar5-icesheets",
        "ipccar5-glaciers",
        "fair-temperature",
    ]
    workflow_modules_list = [
        "ipccar5-icesheets",
        "ipccar5-glaciers",
    ]
    _validate_modules_list_workflow(workflow_modules_list, experiment_modules_list)


def test_validate_modules_list_workflow_fails_for_invalid():
    experiment_modules_list = [
        "ipccar5-icesheets",
        "ipccar5-glaciers",
        "fair-temperature",
    ]
    workflow_modules_list = [
        "ipccar5-icesheets",
        "ipccar5-glaciers",
        "tlm-sterodynamics",
    ]
    with pytest.raises(click.UsageError):
        _validate_modules_list_workflow(workflow_modules_list, experiment_modules_list)
