import yaml
from pathlib import Path
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.infra.path_manager import find_module_yaml_path
from facts_experiment_builder.infra.exceptions import ModuleYamlNotFoundError


def load_facts_module_from_yaml(yaml_path: Path) -> ModuleSchema:
    """
    Load a ModuleSchema from a module YAML file.

    Args:
        yaml_path: Path to the module YAML file.

    Returns:
        ModuleSchema with required and optional fields normalized.
    """
    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise ModuleYamlNotFoundError
    return ModuleSchema.from_dict(data)


def load_facts_module_by_name(module_name: str) -> ModuleSchema:
    """
    Load a ModuleSchema by module name (resolve path then load).

    Args:
        module_name: Module name (e.g. 'fair', 'bamber19-icesheets').
        project_root: Project root directory.

    Returns:
        ModuleSchema for the module.
    """
    yaml_path = find_module_yaml_path(module_name)
    return load_facts_module_from_yaml(yaml_path)
