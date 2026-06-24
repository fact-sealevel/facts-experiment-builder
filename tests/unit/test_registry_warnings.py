import logging
import subprocess
from unittest.mock import MagicMock, patch


from facts_experiment_builder.core.registry.module_registry import (
    _warn_if_registry_behind,
    _warn_if_registry_dirty,
)

_PATCH = "facts_experiment_builder.core.registry.module_registry.subprocess.run"
_LOGGER = "facts_experiment_builder.core.registry.module_registry"


def _run(returncode=0, stdout=""):
    return MagicMock(returncode=returncode, stdout=stdout)


# ---------------------------------------------------------------------------
# _warn_if_registry_behind
# ---------------------------------------------------------------------------


def test_no_warning_when_up_to_date(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, side_effect=[_run(), _run(stdout="0")]):
            _warn_if_registry_behind(tmp_path)
    assert len(caplog.records) == 0


def test_warns_with_commit_count_when_behind(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, side_effect=[_run(), _run(stdout="3")]):
            _warn_if_registry_behind(tmp_path)
    assert any("3 commit(s) behind" in r.message for r in caplog.records)


def test_warns_on_fetch_timeout(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5)):
            _warn_if_registry_behind(tmp_path)
    assert any("Could not check" in r.message for r in caplog.records)


def test_warns_on_git_not_found(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, side_effect=FileNotFoundError("git not found")):
            _warn_if_registry_behind(tmp_path)
    assert any("Could not check" in r.message for r in caplog.records)


def test_warns_on_os_error(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, side_effect=OSError("permission denied")):
            _warn_if_registry_behind(tmp_path)
    assert any("Could not check" in r.message for r in caplog.records)


def test_no_warning_when_no_upstream_tracking_branch(tmp_path, caplog):
    """rev-list returns non-zero when no upstream is configured — no warning."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, side_effect=[_run(), _run(returncode=128, stdout="")]):
            _warn_if_registry_behind(tmp_path)
    assert len(caplog.records) == 0


def test_rev_list_not_called_after_fetch_failure(tmp_path, caplog):
    """If fetch raises, rev-list must not be called."""
    with patch(_PATCH, side_effect=FileNotFoundError("git not found")) as mock_run:
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            _warn_if_registry_behind(tmp_path)
    mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# _warn_if_registry_dirty
# ---------------------------------------------------------------------------


def test_dirty_no_warning_when_clean(tmp_path, caplog):
    """returncode=0, empty stdout → no warning."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, return_value=_run(stdout="")):
            _warn_if_registry_dirty(tmp_path)
    assert len(caplog.records) == 0


def test_dirty_warns_when_uncommitted_changes(tmp_path, caplog):
    """returncode=0, non-empty stdout → logger.warning fires."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, return_value=_run(stdout=" M some_file.yaml\n")):
            _warn_if_registry_dirty(tmp_path)
    assert any("uncommitted changes" in r.message for r in caplog.records)


def test_dirty_no_warning_on_git_error(tmp_path, caplog):
    """Non-zero returncode → no warning (git error treated as not-dirty)."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        with patch(_PATCH, return_value=_run(returncode=128, stdout="")):
            _warn_if_registry_dirty(tmp_path)
    assert len(caplog.records) == 0
