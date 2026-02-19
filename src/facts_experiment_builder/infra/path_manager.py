from pathlib import Path
from typing import Optional
from facts_experiment_builder.resources import get_module_configs_dir
from facts_experiment_builder.infra.path_utils import find_project_root

def get_module_defaults_path(module_name: str) -> Optional[Path]:
    """Get the path to the defaults file for a module (uses shared config location)."""
    from facts_experiment_builder.resources import get_module_configs_dir

    mod_snake = module_name.replace("-", "_")
    configs_dir = get_module_configs_dir()
    # Try defaults_{module}.yml then {module}_defaults.yml
    for name in (f"defaults_{mod_snake}.yml", f"{mod_snake}_defaults.yml"):
        path = configs_dir / name
        if path.exists():
            return path
    return None

def find_module_yaml_path(module_name: str, project_root: Path) -> Path:
    """
    Resolve the path to a module's YAML file by module name.

    Uses the same filename conventions and special cases (e.g. fair /
    fair-temperature) as used by setup and the generic parser.

    Args:
        module_name: Module name (e.g. 'fair', 'bamber19-icesheets').
        project_root: Project root (directory containing pyproject.toml).

    Returns:
        Path to the module YAML file.

    Raises:
        FileNotFoundError: If no matching module YAML is found.
    """
    modules_dir = get_module_configs_dir()
    module_dir_name = module_name.replace("-", "_")

    possible_paths = [
        modules_dir / f"{module_dir_name}_module.yaml",
        modules_dir / f"{module_name}_module.yaml",
    ]

    if module_name == "fair" or module_name.startswith("fair"):
        possible_paths.extend([
            modules_dir / "fair_temperature_module.yaml",
            modules_dir / "fair_module.yaml",
        ])

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Module YAML file not found for module '{module_name}'. "
        f"Tried paths: {[str(p) for p in possible_paths]}"
    )

def find_experiment_metadata_file(experiment_name:str):

    #Resolve path to experiment directory
    project_root = find_project_root()
    experiment_dir = project_root / "experiments" / experiment_name

    if not experiment_dir.exists():
        raise FileNotFoundError(f"Experiment directory not found: {experiment_dir}")

    #Resolve absolute path to file
    metadata_file = experiment_dir / "experiment-metadata.yml"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Experiment metadata file not found: {metadata_file}")

    return metadata_file

def resolve_experiment_compose_path(
    metadata_path:Path,
    custom_output_path:Optional[Path] = None) -> Path:

    if custom_output_path:
        output_path = Path(custom_output_path).resolve()
    else:
        output_path = metadata_path.parent / "experiment-compose.yaml"

    return output_path

