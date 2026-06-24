import subprocess
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class ModuleRegistry:
    def __init__(self, registry_dir: Path):
        self._registry_dir = registry_dir

    @property
    def registry_dir(self) -> Path:
        return self._registry_dir

    @classmethod
    def default(cls) -> "ModuleRegistry":
        return _get_default_registry()

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


@lru_cache(maxsize=1)
def _get_default_registry() -> "ModuleRegistry":
    """Return the default ModuleRegistry, cached for the lifetime of the process.

    Git health checks (_warn_if_registry_dirty, _warn_if_registry_behind) run
    exactly once. Call .cache_clear() in tests that change the working directory
    between cases.
    """
    env_dir = os.environ.get("FEB_MODULE_REGISTRY_DIR")
    if env_dir:
        return ModuleRegistry(Path(env_dir))
    workspace_dir = Path.cwd() / "facts-module-registry"
    if workspace_dir.exists():
        _warn_if_registry_dirty(workspace_dir)
        _warn_if_registry_behind(workspace_dir)
        return ModuleRegistry(workspace_dir)
    raise FileNotFoundError(
        f"Module registry not found. Expected facts-module-registry/ in your "
        f"project workspace ({Path.cwd()}).\n"
        f"Clone it with:\n"
        f"  git clone https://github.com/fact-sealevel/facts-module-registry.git"
    )


def _check_if_registry_behind(registry_dir: Path) -> None:
    """Check if local registry is behind remote.

    Runs `git fetch` (no explicit remote name) so that all configured remotes
    are contacted and all tracking refs are updated — regardless of whether the
    remote is named 'origin', 'upstream', or anything else. Then compares HEAD
    to @{u} (the upstream tracking branch) using `git rev-list HEAD..@{u}
    --count`."""
    try:
        subprocess.run(
            ["git", "fetch"],
            cwd=registry_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning("Could not check facts-module-registry for updates: %s", e)
        return

    result = subprocess.run(
        ["git", "rev-list", "HEAD..@{u}", "--count"],
        cwd=registry_dir,
        capture_output=True,
        text=True,
    )
    return result


def _warn_if_registry_behind(registry_dir: Path) -> None:
    """Warn if the local registry clone is behind its remote tracking branch.

    If the count is non-zero the user is warned with the number of commits they
    are behind. If the fetch fails (timeout, git unavailable, or other OS error)
    a warning is emitted by _check_if_registry_behind and None is returned here —
    in that case we return early. A non-zero rev-list return code (e.g. no
    upstream tracking branch configured) is treated as up-to-date and produces
    no warning.
    """
    result = _check_if_registry_behind(registry_dir=registry_dir)

    if result is None:
        return  # warning already emitted by _check_if_registry_behind

    if result.returncode == 0 and result.stdout.strip().isdigit():
        count = int(result.stdout.strip())
        if count > 0:
            logger.warning(
                "facts-module-registry at %s is %d commit(s) behind the remote. "
                "Run `git pull` in that directory to update.",
                registry_dir,
                count,
            )


def _check_if_registry_dirty(registry_dir: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=registry_dir,
        capture_output=True,
        text=True,
    )
    return result


def _warn_if_registry_dirty(registry_dir: Path) -> None:
    result = _check_if_registry_dirty(registry_dir=registry_dir)

    if result.returncode == 0 and result.stdout.strip():
        logger.warning(
            "facts-module-registry at %s has uncommitted changes. "
            "Module definitions may differ from the published registry.",
            registry_dir,
        )
