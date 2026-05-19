"""Application logic for checking a FACTS data directory against the module registry.

Inspects module_specific_input_data/ and shared_input_data/ directories and
verifies that expected input files declared in each module's YAML are present.
Has no Click or console imports — all output decisions belong to the CLI layer.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from facts_experiment_builder.core.registry.module_registry import ModuleRegistry
from facts_experiment_builder.infra.module_loader import load_facts_module_from_yaml
from facts_experiment_builder.infra.path_utils import is_shared_input


@dataclass
class InputFileCheck:
    field_name: str
    expected_path: Path
    exists: bool
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class ModuleCheckResult:
    module_name: str
    checks: List[InputFileCheck] = field(default_factory=list)

    @property
    def n_present(self) -> int:
        return sum(1 for c in self.checks if not c.skipped and c.exists)

    @property
    def n_missing(self) -> int:
        return sum(1 for c in self.checks if not c.skipped and not c.exists)

    @property
    def n_checkable(self) -> int:
        return sum(1 for c in self.checks if not c.skipped)


@dataclass
class DataCheckResult:
    module_results: List[ModuleCheckResult] = field(default_factory=list)
    shared_checks: List[InputFileCheck] = field(default_factory=list)
    unrecognized_dirs: List[str] = field(default_factory=list)


def _dir_to_module_names(dir_name: str, known_modules: frozenset) -> List[str]:
    """Map a data directory name to one or more module names.

    Handles the multi-command module case where a shared directory (e.g. 'ipccar5')
    provides input data for multiple modules (e.g. 'ipccar5-glaciers', 'ipccar5-icesheets').
    """
    if dir_name in known_modules:
        return [dir_name]
    matches = [m for m in known_modules if m.startswith(dir_name + "-")]
    return sorted(matches)


_MODULE_SPECIFIC_CONTAINER_PATH = "/mnt/module_specific_in"


def _check_module(
    module_name: str,
    module_input_dir: Path,
    registry: ModuleRegistry,
) -> ModuleCheckResult:
    """Check all module-specific input files for one module.

    Covers both the ``inputs`` section and any ``fingerprint_params`` entries
    that mount from module-specific storage.  Shared inputs (fingerprint dirs,
    location files) are excluded here and handled separately by
    check_shared_data().
    """
    result = ModuleCheckResult(module_name=module_name)

    try:
        yaml_path = registry.get_module_yaml_path(module_name)
        schema = load_facts_module_from_yaml(yaml_path)
    except FileNotFoundError:
        return result

    for inp in schema.arguments.get("inputs", []):
        field_name = inp.get("name", "")
        filename = inp.get("filename")
        mount_volume = inp.get("mount", {}).get("volume", "")

        # Skip inputs that come from another module's output (e.g. climate-data-file).
        if mount_volume == "output":
            result.checks.append(
                InputFileCheck(
                    field_name=field_name,
                    expected_path=Path(),
                    exists=False,
                    skipped=True,
                    skip_reason="inter-module dependency (produced by another module at runtime)",
                )
            )
            continue

        # Shared inputs are checked as a group in check_shared_data().
        if is_shared_input(field_name):
            continue

        # Skip inputs without a static filename (filename depends on experiment options).
        if not filename:
            result.checks.append(
                InputFileCheck(
                    field_name=field_name,
                    expected_path=Path(),
                    exists=False,
                    skipped=True,
                    skip_reason="cannot verify without experiment config (filename depends on options)",
                )
            )
            continue

        filenames = filename if isinstance(filename, list) else [filename]

        for fn in filenames:
            expected = module_input_dir / fn
            result.checks.append(
                InputFileCheck(
                    field_name=field_name,
                    expected_path=expected,
                    exists=expected.exists(),
                )
            )

    # Also check fingerprint_params that mount from module-specific storage.
    # Most fingerprint_params use shared storage (/mnt/shared_in) and are
    # handled by check_shared_data(); only those with an explicit
    # module-specific container path are checked here.
    for fp in schema.arguments.get("fingerprint_params", []):
        field_name = fp.get("name", "")
        filename = fp.get("filename")
        container_path = fp.get("mount", {}).get("container_path", "")

        if container_path != _MODULE_SPECIFIC_CONTAINER_PATH:
            continue

        if not filename:
            result.checks.append(
                InputFileCheck(
                    field_name=field_name,
                    expected_path=Path(),
                    exists=False,
                    skipped=True,
                    skip_reason="cannot verify without experiment config (filename depends on options)",
                )
            )
            continue

        filenames = filename if isinstance(filename, list) else [filename]
        for fn in filenames:
            expected = module_input_dir / fn
            result.checks.append(
                InputFileCheck(
                    field_name=field_name,
                    expected_path=expected,
                    exists=expected.exists(),
                )
            )

    return result


_SHARED_CONTAINER_PATH = "/mnt/shared_in"


def check_shared_data(
    discovered_module_names: List[str],
    shared_input_dir: Path,
    registry: ModuleRegistry,
) -> List[InputFileCheck]:
    """Check shared input files required by the discovered modules.

    Collects all unique shared inputs across all discovered modules from two
    argument sections:
    - inputs: entries where is_shared_input(field_name) is True
    - fingerprint_params: entries where mount.container_path is /mnt/shared_in

    Deduplicates by filename so each shared file is reported once.
    """
    seen: set = set()
    checks: List[InputFileCheck] = []

    for module_name in discovered_module_names:
        try:
            yaml_path = registry.get_module_yaml_path(module_name)
            schema = load_facts_module_from_yaml(yaml_path)
        except FileNotFoundError:
            continue

        # Collect (field_name, filename) pairs from both relevant sections.
        candidates = []

        for inp in schema.arguments.get("inputs", []):
            field_name = inp.get("name", "")
            filename = inp.get("filename")
            mount_volume = inp.get("mount", {}).get("volume", "")
            if mount_volume == "output" or not filename:
                continue
            if is_shared_input(field_name):
                candidates.append((field_name, filename))

        for fp in schema.arguments.get("fingerprint_params", []):
            field_name = fp.get("name", "")
            filename = fp.get("filename")
            container_path = fp.get("mount", {}).get("container_path", "")
            if not filename or container_path != _SHARED_CONTAINER_PATH:
                continue
            candidates.append((field_name, filename))

        for field_name, filename in candidates:
            filenames = filename if isinstance(filename, list) else [filename]
            for fn in filenames:
                if fn in seen:
                    continue
                seen.add(fn)
                expected = shared_input_dir / fn
                checks.append(
                    InputFileCheck(
                        field_name=field_name,
                        expected_path=expected,
                        exists=expected.exists(),
                    )
                )

    return checks


def check_module_data(
    module_specific_input_dir: Path,
    shared_input_dir: Path,
    registry: ModuleRegistry,
) -> DataCheckResult:
    """Check data directories against expected module inputs from the registry.

    Scans module_specific_input_dir for subdirectories, matches each to known
    module names, verifies module-specific input files, and checks shared inputs
    required across all discovered modules.
    """
    result = DataCheckResult()

    if not module_specific_input_dir.exists():
        return result

    known_modules = frozenset(registry.list_modules())

    for entry in sorted(module_specific_input_dir.iterdir()):
        if not entry.is_dir():
            continue

        modules = _dir_to_module_names(entry.name, known_modules)
        if not modules:
            result.unrecognized_dirs.append(entry.name)
            continue

        for module_name in modules:
            result.module_results.append(
                _check_module(
                    module_name=module_name,
                    module_input_dir=entry,
                    registry=registry,
                )
            )

    discovered_names = [r.module_name for r in result.module_results]
    result.shared_checks = check_shared_data(discovered_names, shared_input_dir, registry)

    return result
