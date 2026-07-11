from pathlib import Path
from facts_experiment_builder.core.module.module_schema import ModuleSchema

import subprocess
from pydantic import ValidationError
import yaml
from facts_experiment_builder.infra.exceptions import ModuleYamlNotFoundError


class ModuleRegistryNotFound(Exception):
    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"Registry path '{path} not found.")


class FileSystemModuleRegistry:
    def __init__(self, registry_path: Path):
        if not registry_path.is_absolute():
            raise ValueError("registry path must be absolute")
        if not registry_path.is_dir():
            raise ModuleRegistryNotFound(registry_path)

        self._registry_path = registry_path
        self._schemas: dict[str, ModuleSchema] = {}
        self._names: frozenset | None = None

    def _yaml_path(self, module_name: str) -> Path:
        """From a module name, returns path to module yaml within registry."""
        registry_path = self._registry_path
        snake_module_name = module_name.replace("-", "_")
        yaml_path = Path(registry_path, module_name, f"{snake_module_name}_module.yaml")
        return yaml_path

    def get_schema(self, module_name: str) -> ModuleSchema:
        if module_name not in self._schemas:
            path = self._yaml_path(module_name)
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                raise ModuleYamlNotFoundError
            except ValidationError as e:
                raise ModuleSchemaInvalidError(
                    module_name=module_name, path=path, e=e
                ) from e
            module_schema = ModuleSchema.from_dict(data)
            # some modules have an additional file in the registry entry
            mapping_path = (
                path.parent
                / f"scenario_name_mapping_{module_name.replace('-', '_')}.yaml"
            )  # TODO Fix this
            if mapping_path.exists():
                with open(mapping_path) as f:
                    m = yaml.safe_load(f)
                if isinstance(m, dict):
                    module_schema.extra["scenario_name_mapping"] = m
            self._schemas[module_name] = module_schema
        return self._schemas[module_name]

    def module_names(self) -> frozenset[str]:
        if self._names is None:
            names_init = [d.name for d in self._registry_path.iterdir() if d.is_dir()]
            names = frozenset(i for i in names_init if not i.startswith("."))
            self._names = names
        return self._names

    def version(self) -> str:
        """Return the registry git commit hash, or 'unknown' if not a git repo."""
        try:  # TODO fix this
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self._registry_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"local@{result.stdout.strip()}"
        except Exception:
            pass
        return "unknown"


class ModuleSchemaInvalidError(Exception):
    def __init__(self, module_name, path, e):
        super().__init__(f"Invalid module definition for '{module_name}' ({path}): {e}")
