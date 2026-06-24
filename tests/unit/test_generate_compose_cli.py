"""Tests for generate_compose_cli error handling."""

from unittest.mock import patch
from click.testing import CliRunner

from facts_experiment_builder.cli.generate_compose_cli import main

runner = CliRunner()


def _invoke(experiment_name="my-exp"):
    return runner.invoke(main, ["--experiment-name", experiment_name])


def test_file_not_found_error_exits_nonzero():
    """A FileNotFoundError from generate_compose_from_path exits with code 1."""
    with (
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.find_experiment_metadata_file",
            return_value="/fake/path/experiment-config.yaml",
        ),
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.generate_compose_from_path",
            side_effect=FileNotFoundError("metadata file not found: /fake/path"),
        ),
    ):
        result = _invoke()

    assert result.exit_code == 1


def test_file_not_found_error_prints_message():
    """A FileNotFoundError prints a user-facing failure message."""
    with (
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.find_experiment_metadata_file",
            return_value="/fake/path/experiment-config.yaml",
        ),
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.generate_compose_from_path",
            side_effect=FileNotFoundError("metadata file not found: /fake/path"),
        ),
    ):
        result = _invoke()

    assert "Failed to generate compose file" in result.output


def test_value_error_exits_nonzero():
    """A ValueError from generate_compose_from_path exits with code 1."""
    with (
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.find_experiment_metadata_file",
            return_value="/fake/path/experiment-config.yaml",
        ),
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.generate_compose_from_path",
            side_effect=ValueError("No modules could be created from metadata"),
        ),
    ):
        result = _invoke()

    assert result.exit_code == 1


def test_value_error_prints_message():
    """A ValueError prints a user-facing failure message including the error detail."""
    error_detail = "No modules could be created from metadata"
    with (
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.find_experiment_metadata_file",
            return_value="/fake/path/experiment-config.yaml",
        ),
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.generate_compose_from_path",
            side_effect=ValueError(error_detail),
        ),
    ):
        result = _invoke()

    assert "Failed to generate compose file" in result.output
    assert error_detail in result.output
