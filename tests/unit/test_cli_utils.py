"""Unit tests for cli/utils.py."""

import logging

from facts_experiment_builder.cli.utils import (
    configure_logging,
)


def test_determine_root_resolves_correctly_with_alternate_root(tmp_path):
    cli_root = tmp_path / "my_other_working_dir"
    cli_root.mkdir()
    resolved_root = determine_root(cli_root=cli_root)
    assert resolved_root == cli_root.resolve()
    assert resolved_root.is_absolute()


def test_determine_root_resolves_correctly_with_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli_root = None
    resolved_root = determine_root(cli_root)
    assert resolved_root == tmp_path.resolve()
    assert resolved_root.is_absolute()


def test_configure_logging_returns_none_correctly():
    debug_target = None
    assert configure_logging(debug_target) is None


def test_configure_logging_sets_name_when_debug_target_all():
    debug_target = "all"
    configure_logging(debug_target)
    assert logging.getLogger().level == logging.INFO
