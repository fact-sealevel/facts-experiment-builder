"""Minimal pytest suite for setup_new_experiment_cli."""

from click.testing import CliRunner
import click
from facts_experiment_builder.cli.setup_new_experiment_cli import (
    main,
    _validate_modules_list_experiment,
    _validate_modules_list_workflow,
    _check_experiment_step,
)
import pytest
from contextlib import nullcontext


runner = CliRunner()


def test_cli_help_exits_zero():
    """--help runs and exits with 0."""
    result = runner.invoke(main, ["--help"])
    print("output: ", result.output)
    assert result.exit_code == 0
    assert "experiment-name" in result.output
    assert "climate-step" in result.output
    assert "sealevel-step" in result.output
    assert "totaling-step" in result.output
    assert "extremesealevel-step" in result.output


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
            "--climate-step",
            "fair-temperature",
            "--sealevel-step",
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


@pytest.mark.parametrize(
    "step_module, step_data, expectation",
    [
        ("a-module", None, nullcontext()),
        (None, "/path/to/data", nullcontext()),
        ("a-module", "/path/to/data", pytest.raises(click.UsageError)),
        (None, None, pytest.raises(click.UsageError)),
    ],
)
def test_check_experiment_step(step_module, step_data, expectation):
    with expectation:
        _check_experiment_step(step_module, step_data, "--step-module", "--step-data")
