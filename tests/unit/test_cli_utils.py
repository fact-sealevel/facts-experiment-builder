"""Unit tests for cli/utils.py."""

import logging

from facts_experiment_builder.cli.utils import (
    configure_logging,
)


def test_configure_logging_returns_none_correctly():
    debug_target = None
    assert configure_logging(debug_target) is None


def test_configure_logging_sets_name_when_debug_target_all():
    debug_target = "all"
    configure_logging(debug_target)
    assert logging.getLogger().level == logging.INFO
