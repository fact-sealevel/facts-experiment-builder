from pathlib import Path
from typing import Optional
from facts_experiment_builder.core.registry import ModuleRegistry


def get_module_defaults_path(module_name: str) -> Optional[Path]:
    """Get the path to the defaults file for a module."""
    return ModuleRegistry.default().get_module_defaults_path(module_name)


def find_module_yaml_path(module_name: str, project_root: Path) -> Path:
    """
    Resolve the path to a module's YAML file by module name.

    Args:
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets').
        project_root: Project root (unused; kept for backwards compatibility).

    Returns:
        Path to the module YAML file.

    Raises:
        FileNotFoundError: If no matching module YAML is found.
    """
    return ModuleRegistry.default().get_module_yaml_path(module_name)


def find_experiment_metadata_file(experiment_name: str):
    # Resolve path to experiment directory
    project_root = Path.cwd()
    experiment_dir = project_root / "experiments" / experiment_name

    if not experiment_dir.exists():
        raise FileNotFoundError(f"Experiment directory not found: {experiment_dir}")

    # Resolve absolute path to file
    metadata_file = experiment_dir / "experiment-metadata.yml"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Experiment metadata file not found: {metadata_file}")

    return metadata_file


def resolve_experiment_compose_path(
    metadata_path: Path, custom_output_path: Optional[Path] = None
) -> Path:
    if custom_output_path:
        output_path = Path(custom_output_path).resolve()
    else:
        output_path = metadata_path.parent / "experiment-compose.yaml"

    return output_path
