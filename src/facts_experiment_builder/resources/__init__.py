"""Bundled module definitions and defaults (YAML configs)."""

from pathlib import Path


def get_module_configs_dir() -> Path:
    """
    Directory containing bundled module YAMLs and default value files.

    Single source of truth for the config location: if you move the configs
    (e.g. to a different package or repo), change only this return value.
    """
    return Path(__file__).resolve().parent / "configs"
