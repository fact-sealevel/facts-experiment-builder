import subprocess
import warnings
from unittest.mock import MagicMock, patch

import pytest

from facts_experiment_builder.core.registry.module_registry import (
    _warn_if_registry_behind,
)

_PATCH = "facts_experiment_builder.core.registry.module_registry.subprocess.run"


def _run(returncode=0, stdout=""):
    return MagicMock(returncode=returncode, stdout=stdout)


# ---------------------------------------------------------------------------
# _warn_if_registry_behind
# ---------------------------------------------------------------------------


def test_no_warning_when_up_to_date(tmp_path):
    with patch(_PATCH, side_effect=[_run(), _run(stdout="0")]):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _warn_if_registry_behind(tmp_path)
    assert len(w) == 0


def test_warns_with_commit_count_when_behind(tmp_path):
    with patch(_PATCH, side_effect=[_run(), _run(stdout="3")]):
        with pytest.warns(UserWarning, match="3 commit\\(s\\) behind"):
            _warn_if_registry_behind(tmp_path)


def test_warns_on_fetch_timeout(tmp_path):
    with patch(_PATCH, side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5)):
        with pytest.warns(UserWarning, match="Could not check"):
            _warn_if_registry_behind(tmp_path)


def test_warns_on_git_not_found(tmp_path):
    with patch(_PATCH, side_effect=FileNotFoundError("git not found")):
        with pytest.warns(UserWarning, match="Could not check"):
            _warn_if_registry_behind(tmp_path)


def test_warns_on_os_error(tmp_path):
    with patch(_PATCH, side_effect=OSError("permission denied")):
        with pytest.warns(UserWarning, match="Could not check"):
            _warn_if_registry_behind(tmp_path)


def test_no_warning_when_no_upstream_tracking_branch(tmp_path):
    """rev-list returns non-zero when no upstream is configured — no warning."""
    with patch(_PATCH, side_effect=[_run(), _run(returncode=128, stdout="")]):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _warn_if_registry_behind(tmp_path)
    assert len(w) == 0


def test_rev_list_not_called_after_fetch_failure(tmp_path):
    """If fetch raises, rev-list must not be called."""
    with patch(_PATCH, side_effect=FileNotFoundError("git not found")) as mock_run:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            _warn_if_registry_behind(tmp_path)
    mock_run.assert_called_once()
