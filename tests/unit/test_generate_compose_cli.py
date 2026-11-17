from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from facts_experiment_builder.cli.generate_compose_cli import main
from facts_experiment_builder.io.compose_backend import ComposeBackend

runner = CliRunner()


def test_custom_compose_path_is_passed_as_a_path(tmp_path):
    """--custom-compose-path reaches generate_run_file() as a Path, which it
    resolves."""
    custom = tmp_path / "custom" / "experiment-compose.yaml"
    custom.parent.mkdir()

    with patch(
        "facts_experiment_builder.cli.generate_compose_cli.generate_run_file"
    ) as mock_generate:
        mock_generate.return_value.path = Path.cwd() / "experiment-compose.yaml"
        result = runner.invoke(
            main,
            [
                "--experiment-name",
                "exp",
                "--workspace-dir",
                str(tmp_path),
                "--custom-compose-path",
                str(custom),
            ],
        )

    assert result.exit_code == 0, result.output
    kwargs = mock_generate.call_args.kwargs
    assert isinstance(kwargs["backend"], ComposeBackend)
    assert isinstance(kwargs["custom_output_path"], Path)
    assert kwargs["custom_output_path"] == custom


def test_compose_path_outside_current_directory_is_printed_as_is(tmp_path):
    """The workspace need not be under the current directory; the next-steps line
    prints the compose file's absolute path."""
    compose_path = tmp_path / "experiments" / "exp" / "experiment-compose.yaml"
    assert not compose_path.is_relative_to(Path.cwd())

    with (
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.generate_run_file"
        ) as mock_generate,
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.console"
        ) as mock_console,
    ):
        mock_generate.return_value.path = compose_path
        result = runner.invoke(
            main, ["--experiment-name", "exp", "--workspace-dir", str(tmp_path)]
        )

    assert result.exit_code == 0, result.output
    printed = [c.args[0] for c in mock_console.print.call_args_list if c.args]
    assert any(f"docker compose -f {compose_path} up" in p for p in printed)
