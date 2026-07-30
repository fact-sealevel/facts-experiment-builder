"""Minimal pytest suite for setup_experiment_cli."""

from click.testing import CliRunner
from facts_experiment_builder.cli.setup_experiment_cli import (
    main,
)
from pathlib import Path





runner = CliRunner()


def test_cli_help_exits_zero():
    """--help runs and exits with 0."""
    result = runner.invoke(main, ["--help"])
    # Assert that the program runs successfully if --help passed
    assert result.exit_code == 0
    # Assert that arg names are in output
    assert "experiment-name" in result.output
    assert "climate-step" in result.output
    assert "sealevel-step" in result.output
    assert "extremesealevel-step" in result.output


def test_cli_fails_without_required_args():
    """Invoking without required options exits non-zero."""
    result = runner.invoke(main, [])
    print("result output: ", result.output)
    # assert that program doesn't run successfully if requried args missing
    assert result.exit_code != 0
    # Assert that the output contains informative message about whats missing
    assert (
        "experiment-name" in result.output
        or "Missing" in result.output
        or "Error" in result.output
    )


def test_cli_succeeds_with_existing_dir_as_workspace_dir(tmp_path, fake_registry):
    registry = fake_registry(
        {
            "fair-temperature": {"module_name": "fair-temperature"},
            "ipccar5-icesheets": {"module_name": "ipccar5-icesheets"},
            "ipccar5-glaciers": {"module_name": "ipccar5-icesheets"},
            "facts-total": {"module_name": "facts-total"},
        }
    )

    workspace_dir = Path(tmp_path, "workspace")
    workspace_dir.mkdir()

    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--climate-step",
            "fair-temperature",
            "--workspace-dir",
            str(workspace_dir),
            "--module-registry",
            str(registry),
        ],
    )
    assert result.exit_code == 0, (
        f" exit_code={result.exit_code}\n"
        f" --- output ---\n{result.output}\n"
        f" -- exception ---\n{result.exception!r}"
    )


def test_cli_fails_with_nonexisting_dir_as_workspace_dir(tmp_path, fake_registry):
    registry = fake_registry(
        {
            "fair-temperature": {"module_name": "fair-temperature"},
            "ipccar5-icesheets": {"module_name": "ipccar5-icesheets"},
            "ipccar5-glaciers": {"module_name": "ipccar5-icesheets"},
            "facts-total": {"module_name": "facts-total"},
        }
    )

    workspace_dir = Path(tmp_path, "workspace")

    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--climate-step",
            "fair-temperature",
            "--workspace-dir",
            str(workspace_dir),
            "--module-registry",
            str(registry),
        ],
    )
    assert result.exit_code != 0, (
        f" exit_code={result.exit_code}\n"
        f" --- output ---\n{result.output}\n"
        f" -- exception ---\n{result.exception!r}"
    )
    assert "does not exist." in result.output


def test_cli_fails_with_file_passed_as_workspace_dir(tmp_path, fake_registry):
    registry = fake_registry(
        {
            "fair-temperature": {"module_name": "fair-temperature"},
            "ipccar5-icesheets": {"module_name": "ipccar5-icesheets"},
            "ipccar5-glaciers": {"module_name": "ipccar5-icesheets"},
            "facts-total": {"module_name": "facts-total"},
        }
    )

    workspace_file = Path(tmp_path, "some_file.yaml")
    workspace_dir = Path(tmp_path, "some_dir")
    workspace_dir.mkdir()
    workspace_file.touch()
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--climate-step",
            "fair-temperature",
            "--workspace-dir",
            str(workspace_file),
            "--module-registry",
            str(registry),
        ],
    )
    assert result.exit_code == 2, (
        f" exit_code={result.exit_code}\n"
        f" --- output ---\n{result.output}\n"
        f" -- exception ---\n{result.exception!r}"
    )
    assert "is a file" in result.output


def test_cli_fails_with_file_passed_as_module_registry(tmp_path):
    registry_file = Path(tmp_path, "some_file.yaml")
    workspace_dir = Path(tmp_path, "some_dir")
    workspace_dir.mkdir()
    registry_file.touch()
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--climate-step",
            "fair-temperature",
            "--workspace-dir",
            str(workspace_dir),
            "--module-registry",
            str(registry_file),
        ],
    )
    assert result.exit_code == 2, (
        f" exit_code={result.exit_code}\n"
        f" --- output ---\n{result.output}\n"
        f" -- exception ---\n{result.exception!r}"
    )
    assert "is a file" in result.output


def test_setup_experiment_succeeds_with_valid_modules(
    tmp_path, fake_registry, decline_extra_prompts
):
    """Tests that setup experiment cli runs successfully if valid modules are passed.
    Create a fake registry fixture; it must have entries for all modules passed in climate-step etc."""
    registry = fake_registry(
        {
            "fair-temperature": {"module_name": "fair-temperature"},
            "ipccar5-icesheets": {"module_name": "ipccar5-icesheets"},
            "ipccar5-glaciers": {"module_name": "ipccar5-icesheets"},
            "facts-total": {"module_name": "facts-total"},
        }
    )

    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--climate-step",
            "fair-temperature",
            "--sealevel-step",
            "ipccar5-icesheets,ipccar5-glaciers",
            "--workspace-dir",
            str(tmp_path),
            "--module-registry",
            str(registry),
        ],
    )
    assert result.exit_code == 0, (
        f" exit_code={result.exit_code}\n"
        f" --- output ---\n{result.output}\n"
        f" -- exception ---\n{result.exception!r}"
    )


def test_setup_experiment_fails_with_invalid_module_name(
    fake_registry, tmp_path, decline_extra_prompts
):
    """Tests that setup fails if a setup-experiment receives modules that are not in the associated registry."""
    registry = fake_registry(
        {
            "fair-temperature": {"module_name": "fair-temperature"},
            "ipccar5-icesheets": {"module_name": "ipccar5-icesheets"},
            "ipccar5-glaciers": {"module_name": "ipccar5-glaciers"},
            "facts-total": {"module_name": "facts-total"},
        }
    )
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--climate-step",
            "fair-temperature",
            "--sealevel-step",
            "ipccar5-icesheets,ipccar5-glaciers,invalid-module-name",
            "--module-registry",
            str(registry),
            "--workspace-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert 'ValueError("Invalid module name(s)' not in str(result.exception), (
        "Test correctly failed but it is likely failing for a different reason;"
        f" --- output ---\n{result.output}\n"
        f" --- output ---\n{result.exception}\n"
    )


def test_setup_experiment_fails_without_climate_step_info(fake_registry, tmp_path):
    registry = fake_registry({"fake-module": {"module_name": "fake-module"}})
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test-exp",
            "--workspace-dir",
            str(tmp_path),
            "--module-registry",
            str(registry),
        ],
    )
    print("result output: ", result.output)
    assert result.exit_code != 0, (
        f" --- output ---\n{result.output}\n --- output ---\n{result.exception}\n"
    )
    missing_climate_str = "Must pass either a climate module (--climate-step) or climate data (--supplied-climate-step-data)."
    assert missing_climate_str in str(result.exception), (
        "probably failed for wrong reason"
        f" --- output ---\n{result.output}\n"
        f" --- output ---\n{result.exception}\n"
    )


def test_setup_experiment_fails_with_invalid_registry_path(tmp_path):
    invalid_reg_path = Path(tmp_path, "module-registry")
    result = runner.invoke(
        main,
        [
            "--experiment-name",
            "test_exp",
            "--workspace-dir",
            str(tmp_path),
            "--module-registry",
            str(invalid_reg_path),
            "--climate-step",
            "fair-temperature",
        ],
    )
    print(f" --- output ---\n{result.output}\n --- output ---\n{result.exception}\n")
    assert result.exit_code != 0
    assert f"'{invalid_reg_path}' does not exist." in str(result.output)
