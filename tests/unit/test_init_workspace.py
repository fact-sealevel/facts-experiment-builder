"""Unit tests for application/init_workspace.py and cli/init_cli.py."""

from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner

from facts_experiment_builder.application.init_workspace import (
    REGISTRY_URL,
    WORKSPACE_MARKER_FILENAME,
    StepStatus,
    ensure_registry_cloned,
    ensure_workspace_marker,
    init_workspace,
)
from facts_experiment_builder.cli.init_cli import init


# ---------------------------------------------------------------------------
# ensure_experiments_dir
# ---------------------------------------------------------------------------


def test_ensure_experiments_dir_creates(tmp_path):
    from facts_experiment_builder.application.init_workspace import ensure_experiments_dir

    result = ensure_experiments_dir(tmp_path)
    assert result.status == StepStatus.CREATED
    assert (tmp_path / "experiments").is_dir()


def test_ensure_experiments_dir_already_exists(tmp_path):
    from facts_experiment_builder.application.init_workspace import ensure_experiments_dir

    (tmp_path / "experiments").mkdir()
    result = ensure_experiments_dir(tmp_path)
    assert result.status == StepStatus.ALREADY_EXISTS


# ---------------------------------------------------------------------------
# ensure_registry_cloned
# ---------------------------------------------------------------------------


def test_ensure_registry_cloned_clones_when_absent(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = ensure_registry_cloned(tmp_path)
    assert result.status == StepStatus.CREATED
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "git" in call_args
    assert "clone" in call_args
    assert REGISTRY_URL in call_args


def test_ensure_registry_cloned_already_exists(tmp_path):
    (tmp_path / "facts-module-registry").mkdir()
    with patch("subprocess.run") as mock_run:
        result = ensure_registry_cloned(tmp_path)
    mock_run.assert_not_called()
    assert result.status == StepStatus.ALREADY_EXISTS


def test_ensure_registry_cloned_returns_failed_on_nonzero(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stderr="fatal: repository not found"
        )
        result = ensure_registry_cloned(tmp_path)
    assert result.status == StepStatus.FAILED
    assert "fatal: repository not found" in result.message


def test_ensure_registry_cloned_returns_failed_when_git_missing(tmp_path):
    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        result = ensure_registry_cloned(tmp_path)
    assert result.status == StepStatus.FAILED
    assert "git" in result.message.lower()


# ---------------------------------------------------------------------------
# ensure_workspace_marker
# ---------------------------------------------------------------------------


def test_ensure_workspace_marker_creates(tmp_path):
    result = ensure_workspace_marker(tmp_path)
    assert result.status == StepStatus.CREATED
    marker_path = tmp_path / WORKSPACE_MARKER_FILENAME
    assert marker_path.exists()
    contents = yaml.safe_load(marker_path.read_text())
    assert "initialized_at" in contents
    assert contents["registry_url"] == REGISTRY_URL


def test_ensure_workspace_marker_already_exists(tmp_path):
    original = {"initialized_at": "2024-01-01T00:00:00+00:00", "registry_url": REGISTRY_URL}
    marker_path = tmp_path / WORKSPACE_MARKER_FILENAME
    marker_path.write_text(yaml.dump(original))

    result = ensure_workspace_marker(tmp_path)
    assert result.status == StepStatus.ALREADY_EXISTS
    # Original content must be unchanged
    contents = yaml.safe_load(marker_path.read_text())
    assert contents["initialized_at"] == "2024-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# init_workspace (orchestration)
# ---------------------------------------------------------------------------


def test_init_workspace_fresh(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = init_workspace(tmp_path)

    assert result.experiments_dir.status == StepStatus.CREATED
    assert result.registry.status == StepStatus.CREATED
    assert result.marker_file.status == StepStatus.CREATED
    assert (tmp_path / "experiments").is_dir()
    assert (tmp_path / WORKSPACE_MARKER_FILENAME).exists()


def test_init_workspace_idempotent(tmp_path):
    (tmp_path / "experiments").mkdir()
    (tmp_path / "facts-module-registry").mkdir()
    marker_path = tmp_path / WORKSPACE_MARKER_FILENAME
    marker_path.write_text(
        yaml.dump({"initialized_at": "2026-01-01T00:00:00+00:00", "registry_url": REGISTRY_URL})
    )

    with patch("subprocess.run") as mock_run:
        result = init_workspace(tmp_path)

    mock_run.assert_not_called()
    assert result.experiments_dir.status == StepStatus.ALREADY_EXISTS
    assert result.registry.status == StepStatus.ALREADY_EXISTS
    assert result.marker_file.status == StepStatus.ALREADY_EXISTS


def test_init_workspace_clone_failure_skips_marker(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="network error")
        result = init_workspace(tmp_path)

    assert result.registry.status == StepStatus.FAILED
    assert result.marker_file.status == StepStatus.FAILED
    assert not (tmp_path / WORKSPACE_MARKER_FILENAME).exists()
    # experiments/ should still be created even if registry fails
    assert (tmp_path / "experiments").is_dir()


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_init_cli_help():
    runner = CliRunner()
    result = runner.invoke(init, ["--help"])
    assert result.exit_code == 0
    assert "registry-url" in result.output


def test_init_cli_fresh_workspace(tmp_path):
    runner = CliRunner()
    with patch(
        "facts_experiment_builder.application.init_workspace.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = runner.invoke(init, [], catch_exceptions=False, obj=None)
        # CliRunner isolates the filesystem via a context manager, so chdir to tmp_path
    # Run again with the correct cwd
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with patch(
            "facts_experiment_builder.application.init_workspace.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = runner.invoke(init, [])
    assert result.exit_code == 0
    assert "Workspace ready" in result.output


def test_init_cli_clone_failure_exits_nonzero(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with patch(
            "facts_experiment_builder.application.init_workspace.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="fatal: network error")
            result = runner.invoke(init, [])
    assert result.exit_code != 0


def test_init_cli_accepts_custom_registry_url(tmp_path):
    custom_url = "https://github.com/my-fork/facts-module-registry.git"
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with patch(
            "facts_experiment_builder.application.init_workspace.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = runner.invoke(init, ["--registry-url", custom_url])
    assert result.exit_code == 0
    call_args = mock_run.call_args[0][0]
    assert custom_url in call_args
