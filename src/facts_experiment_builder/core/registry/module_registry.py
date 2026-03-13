from pathlib import Path
from typing import List, Optional


class ModuleRegistry:
    def __init__(self, registry_dir: Path):
        self._registry_dir = registry_dir

    @classmethod
    def default(cls) -> "ModuleRegistry":
        from facts_experiment_builder.resources import get_module_registry_dir

        return cls(get_module_registry_dir())

    def get_module_yaml_path(self, module_name: str) -> Path:
        """Return path to <module_name>/<snake>_module.yaml in the registry."""
        snake = module_name.replace("-", "_")
        module_dir = self._registry_dir / module_name
        path = module_dir / f"{snake}_module.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"Module YAML not found for '{module_name}'. Expected: {path}"
            )
        return path

    def get_module_defaults_path(self, module_name: str) -> Optional[Path]:
        """Return path to the defaults file for a module, or None if absent."""
        snake = module_name.replace("-", "_")
        module_dir = self._registry_dir / module_name
        for filename in (f"defaults_{snake}.yml", f"{snake}_defaults.yml"):
            path = module_dir / filename
            if path.exists():
                return path
        return None

    def get_module_file(self, module_name: str, filename: str) -> Path:
        """Return path to an arbitrary file inside a module's registry directory."""
        return self._registry_dir / module_name / filename

    def list_modules(self) -> List[str]:
        """Return names of all module directories in the registry."""
        return [d.name for d in self._registry_dir.iterdir() if d.is_dir()]
