from pathlib import Path
from typing import Optional
from facts_experiment_builder.core.registry import ModuleRegistry


def get_module_defaults_path(module_name: str) -> Optional[Path]:
    """Get the path to the defaults file for a module."""
    return ModuleRegistry.default().get_module_defaults_path(module_name)


def find_module_yaml_path(module_name: str) -> Path:
    """
    Resolve the path to a module's YAML file by module name.

    Args:
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets').

    Returns:
        Path to the module YAML file.

    Raises:
        FileNotFoundError: If no matching module YAML is found.
    """
    return ModuleRegistry.default().get_module_yaml_path(module_name)
