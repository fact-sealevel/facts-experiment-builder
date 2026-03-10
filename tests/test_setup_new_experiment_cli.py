"""Minimal pytest suite for setup_new_experiment_cli."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from facts_experiment_builder.cli.setup_new_experiment_cli import main


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


def test_cli_parses_sealevel_modules():
    """Sealevel modules string is parsed into a list (via mocked app)."""
    with (
        patch(
            "facts_experiment_builder.cli.setup_new_experiment_cli.setup_new_experiment_fs",
            return_value=Path("/tmp/test-exp"),
        ),
        patch(
            "facts_experiment_builder.cli.setup_new_experiment_cli.init_new_experiment",
            return_value=MagicMock(),
        ),
        patch(
            "facts_experiment_builder.cli.setup_new_experiment_cli.populate_experiment_defaults",
        ),
        patch(
            "facts_experiment_builder.cli.setup_new_experiment_cli.write_metadata_yaml_jinja2",
        ),
    ):
        result = runner.invoke(
            main,
            [
                "--experiment-name",
                "test-exp",
                "--temperature-module",
                "fair_temperature",
                "--sealevel-modules",
                "ipccar5_icesheets, ipccar5_glaciers",
            ],
        )
    assert result.exit_code == 0
