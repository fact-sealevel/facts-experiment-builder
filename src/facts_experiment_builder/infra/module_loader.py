import yaml
from pathlib import Path
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.infra.path_manager import find_module_yaml_path


def load_facts_module_from_yaml(yaml_path: Path) -> ModuleSchema:
    """
    Load a ModuleSchema from a module YAML file.

    Args:
        yaml_path: Path to the module YAML file.

    Returns:
        ModuleSchema with required and optional fields normalized.
    """
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f) or {}

    arguments = data.get("arguments", {})
    if not isinstance(arguments, dict):
        arguments = {}
    volumes = data.get("volumes", {})
    if not isinstance(volumes, dict):
        volumes = {}

    known_keys = {
        "module_name",
        "container_image",
        "arguments",
        "volumes",
        "depends_on",
        "command",
        "uses_climate_file",
        "climate_file_required",
    }
    extra = {k: v for k, v in data.items() if k not in known_keys}

    facts_module = ModuleSchema(
        module_name=data.get("module_name", ""),
        container_image=data.get("container_image", ""),
        arguments=arguments,
        volumes=volumes,
        depends_on=data.get("depends_on"),
        command=data.get("command", ""),
        uses_climate_file=data.get("uses_climate_file", False),
        extra=extra,
    )

    return facts_module


def load_facts_module_by_name(module_name: str, project_root: Path) -> ModuleSchema:
    """
    Load a ModuleSchema by module name (resolve path then load).

    Args:
        module_name: Module name (e.g. 'fair', 'bamber19-icesheets').
        project_root: Project root directory.

    Returns:
        ModuleSchema for the module.
    """
    yaml_path = find_module_yaml_path(module_name, project_root)
    return load_facts_module_from_yaml(yaml_path)
