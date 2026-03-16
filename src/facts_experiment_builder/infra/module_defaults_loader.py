from facts_experiment_builder.infra.path_manager import get_module_defaults_path
import yaml


def load_module_defaults(module_name: str) -> dict:
    """Read defaults from defaults.yml file for a module."""
    defaults_yml_path = get_module_defaults_path(module_name)
    if defaults_yml_path:
        with open(defaults_yml_path, "r") as f:
            defaults_yml = yaml.safe_load(f) or {}
        return defaults_yml
    else:
        return {}
