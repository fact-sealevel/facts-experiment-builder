import subprocess
import warnings
from pathlib import Path
from typing import List, Optional


class ModuleRegistry:
    def __init__(self, registry_dir: Path):
        self._registry_dir = registry_dir

    @property
    def registry_dir(self) -> Path:
        return self._registry_dir

    @classmethod
    def default(cls) -> "ModuleRegistry":
        workspace_dir = Path.cwd() / "facts-module-registry"
        if workspace_dir.exists():
            _warn_if_registry_dirty(workspace_dir)
            return cls(workspace_dir)
        raise FileNotFoundError(
            f"Module registry not found. Expected facts-module-registry/ in your "
            f"project workspace ({Path.cwd()}).\n"
            f"Clone it with:\n"
            f"  git clone https://github.com/fact-sealevel/facts-module-registry.git"
        )

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

    def get_version(self) -> str:
        """Return the registry git commit hash, or 'unknown' if not a git repo."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self._registry_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"local@{result.stdout.strip()}"
        except Exception:
            pass
        return "unknown"

    def list_modules(self) -> List[str]:
        """Return names of all module directories in the registry."""
        return [d.name for d in self._registry_dir.iterdir() if d.is_dir()]


def _warn_if_registry_dirty(registry_dir: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=registry_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            warnings.warn(
                f"facts-module-registry at {registry_dir} has uncommitted changes. "
                "Module definitions may differ from the published registry.",
                stacklevel=4,
            )
    except Exception:
        pass
