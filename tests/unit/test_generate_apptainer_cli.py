"""Unit tests for generate_apptainer_cli."""

from click.testing import CliRunner

from facts_experiment_builder.cli.generate_apptainer_cli import main


def test_nonexistent_experiment_name_exits_with_code_1(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--experiment-name", "does_not_exist", "--workspace-dir", str(tmp_path)],
    )
    assert result.exit_code == 1


def test_nonexistent_workspace_dir_fails_click_validation():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "my_experiment",
            "--workspace-dir",
            "/this/path/does/not/exist",
        ],
    )
    # Click validates `exists=True` before the application layer runs
    assert result.exit_code != 0
