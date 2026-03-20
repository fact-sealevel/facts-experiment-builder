from rich.style import Style
from rich.theme import Theme

from facts_experiment_builder.cli.theme import console, lapaz_theme

# Derive custom keys by diffing against Rich's default theme.
# This stays correct automatically if lapaz_theme gains or loses keys.
_DEFAULT_KEYS = set(Theme().styles.keys())
LAPAZ_CUSTOM_KEYS = [k for k in lapaz_theme.styles if k not in _DEFAULT_KEYS]


def test_lapaz_theme_has_custom_keys():
    assert len(LAPAZ_CUSTOM_KEYS) > 0, (
        "lapaz_theme defines no custom keys beyond Rich defaults"
    )


def test_lapaz_theme_values_are_valid_rich_styles():
    for key in LAPAZ_CUSTOM_KEYS:
        value = lapaz_theme.styles[key]
        try:
            Style.parse(str(value))
        except Exception as e:
            raise AssertionError(
                f"Theme key '{key}' has invalid Rich style '{value}': {e}"
            )


def test_console_has_all_lapaz_custom_keys():
    for key in LAPAZ_CUSTOM_KEYS:
        assert console._theme_stack.get(key) is not None, (
            f"Key '{key}' from lapaz_theme not active in console"
        )


def test_console_custom_styles_match_active_theme():
    for key in (
        LAPAZ_CUSTOM_KEYS
    ):  # switch this (and create new key list) to use a different theme
        assert console._theme_stack.get(key) == lapaz_theme.styles[key], (
            f"Console style for '{key}' does not match lapaz_theme — "
            "was the console switched to a different theme?"
        )
