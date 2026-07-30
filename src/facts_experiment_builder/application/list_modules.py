from facts_experiment_builder.io.module_registry import FileSystemModuleRegistry
from pathlib import Path


def list_modules(registry_path: Path) -> tuple[list[str], Path]:
    # get absolute path
    registry_path = registry_path.absolute()

    # make module registry
    module_registry = FileSystemModuleRegistry(registry_path=registry_path)

    # get list of module names in registry
    module_names = module_registry.module_names()

    return (sorted(module_names), registry_path)
