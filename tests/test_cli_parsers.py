"""Tests for CLI input parsers (pure functions, no Click)."""

from facts_experiment_builder.cli.parsers import parse_comma_separated_modules


def test_parse_comma_separated_modules_normal():
    """Comma-separated string is split and stripped."""
    assert parse_comma_separated_modules("a, b , c") == ["a", "b", "c"]


def test_parse_comma_separated_modules_single():
    """Single module name returns one-element list."""
    assert parse_comma_separated_modules("ipccar5_icesheets") == ["ipccar5_icesheets"]


def test_parse_comma_separated_modules_none():
    """None yields empty list."""
    assert parse_comma_separated_modules(None) == []


def test_parse_comma_separated_modules_empty_string():
    """Empty or whitespace-only string yields empty list."""
    assert parse_comma_separated_modules("") == []
    assert parse_comma_separated_modules("   ") == []


def test_parse_comma_separated_modules_skips_empty_parts():
    """Consecutive commas or trailing commas do not add empty strings."""
    assert parse_comma_separated_modules("a,,b, ") == ["a", "b"]
