"""Application logic for checking a FACTS data directory against the module registry.

Inspects module_specific_input_data/ and shared_input_data/ directories and
verifies that expected input files declared in each module's YAML are present.
Has no Click or console imports — all output decisions belong to the CLI layer.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_definition_source import (
    ModuleDefinitionSource,
)
from facts_experiment_builder.core.typed_path import (
    _SHARED_CONTAINER_PATH,
    _MODULE_SPECIFIC_CONTAINER_PATH,
)


@dataclass
class InputFileCheck:
    """Object representing result of checking a single input file.
    CheckModuleResult holds a list of these applied to each input file associated with that module."""

    field_name: str
    expected_path: Path
    exists: bool
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class CheckModuleResult:
    module_name: str
    checks: List[InputFileCheck] = field(default_factory=list)

    @property
    def n_present(self) -> int:
        """Returns number of files checked in a given module"""
        return sum(1 for c in self.checks if not c.skipped and c.exists)

    @property
    def n_missing(self) -> int:
        """Returns number of missing files found in a given module based on comparison with that module in module registry"""
        return sum(1 for c in self.checks if not c.skipped and not c.exists)

    @property
    def n_checkable(self) -> int:
        return sum(1 for c in self.checks if not c.skipped)


@dataclass
class CheckDataResult:
    """Object returned by check_module_data().
    Holds results for checking of individual modules (List[CheckModuleResult]),
    results for check of shared input data dir (List[InputFileCheck]), and
    any unrecognized directories found at the specified location (List[str])."""

    module_results: List[CheckModuleResult] = field(default_factory=list)
    shared_checks: List[InputFileCheck] = field(default_factory=list)
    unrecognized_dirs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlannedCheck:
    """small data class used in _check_module to separate out deciding
    what type of check needs to occur based on mount type, input type etc.
    from the actual checking that occurs (exists())

    Attrs:
    - field_name: str
    - rel_path: str | None
    - skip_reason: str=""
    """

    field_name: str
    rel_path: str | None  # the relative path that will be checked
    skip_reason: str = ""  # the reason for a skip

    def __post_init__(self):
        if self.rel_path is None and self.skip_reason == "":
            raise ValueError(
                f"Received rel_path is '{self.rel_path}' with no skip_reason. If rel_path doesnt exist, must receive valid skip_reason."
            )


def resolve_input_paths(
    data_dir: Path,
    module_specific_input_data: Path | None,
    shared_input_data: Path | None,
) -> tuple[Path, Path]:
    """Resolve and validate module-specific and shared input data paths.

    Valid combinations:
        - data_dir only: expects module_specific_input_data/ and shared_input_data/ subdirs
        - Either or both explicit paths: override the corresponding data_dir-derived subdir
        - Both explicit paths: data_dir is ignored for resolution

    Raises:
        ValueError: if a resolved path does not exist on disk
    """
    module_dir = module_specific_input_data or data_dir / "module_specific_input_data"
    shared_dir = shared_input_data or data_dir / "shared_input_data"

    if not module_dir.exists():
        if module_specific_input_data:
            raise ValueError(
                f"Module-specific input data directory not found: {module_dir}\n"
                "Create it and download module input data first. See the quickstart guide."
            )
        existing_subdirs = [p.name for p in data_dir.iterdir() if p.is_dir()]
        raise ValueError(
            f"Expected subdirectory not found: {data_dir}/module_specific_input_data\n"
            f"Existing subdirectories at {data_dir}: {existing_subdirs}. "
            "Names MUST match 'module_specific_input_data' and 'shared_input_data'\n"
            "Either create this subdirectory and add module data, or specify the correct "
            "path with --module-specific-input-data."
        )

    if not shared_dir.exists():
        if shared_input_data:
            raise ValueError(
                f"Shared input data directory not found: {shared_dir}\n"
                "Create it and add shared input data first. See the quickstart guide."
            )
        raise ValueError(
            f"Expected subdirectory not found: {data_dir}/shared_input_data\n"
            "Either create this subdirectory and add shared data, or specify the correct "
            "path with --shared-input-data."
        )

    return module_dir, shared_dir


def _dir_to_module_names(dir_name: str, known_modules: frozenset) -> List[str]:
    """Map a data directory name to one or more module names.

    Handles the multi-command module case where a shared directory (e.g. 'ipccar5')
    provides input data for multiple modules (e.g. 'ipccar5-glaciers', 'ipccar5-icesheets').

    Returns a sorted list of all modules
    """
    if dir_name in known_modules:
        return [dir_name]
    matches = [m for m in known_modules if m.startswith(dir_name + "-")]
    return sorted(matches)


def plan_fp_checks(entry: Dict[str, dict]) -> List[PlannedCheck]:
    field_name = entry.get("name", "")
    container_path = entry.get("mount", {}).get("container_path", "")

    if container_path != _MODULE_SPECIFIC_CONTAINER_PATH:
        return [
            PlannedCheck(field_name, None, "uses shared fp data, checked elsewhere.")
        ]
    match entry.get("type"):
        case "file":
            raw = entry.get("filename")
        case "dir":
            raw = entry.get("default_value")
        case _:
            raw = None
    if raw is None:
        return [
            PlannedCheck(
                field_name=field_name,
                rel_path=None,
                skip_reason="Cannot verify without experiment config (filename depends on options)",
            )
        ]
    paths = raw if isinstance(raw, list) else [raw]
    return [PlannedCheck(field_name, p) for p in paths]


def plan_input_checks(inp: Dict[str, dict]) -> List[PlannedCheck]:
    """Fn to decide what to check for a given input entry."""

    field_name = inp.get("name", "")
    if inp.get("mount", {}).get("volume", "") == "output":
        return [
            PlannedCheck(
                field_name,
                None,
                "inter-module dep. (generated by another module at runtime)",
            )
        ]
    if inp.get("mount", {}).get("container_path") == "/mnt/shared_in":
        return []

    match inp.get("type"):
        case "file":
            raw = inp.get("filename")
        case "dir":
            raw = inp.get("default_value")
        case _:
            raw = None
    if raw is None:
        return [
            PlannedCheck(
                field_name=field_name,
                rel_path=None,
                skip_reason="Cannot verify without experiment config (filename depends on options)",
            )
        ]
    paths = raw if isinstance(raw, list) else [raw]
    return [PlannedCheck(field_name, p) for p in paths]


def execute_check(plan: PlannedCheck, module_input_dir: Path) -> InputFileCheck:
    assert isinstance(plan, PlannedCheck), (
        f"Expected type(plan) == PlannedCheck. instead received '{type(plan)}"
    )
    assert isinstance(module_input_dir, Path), (
        f"Expected type(module_input_dir) == Path, received '{type(module_input_dir)}"
    )
    # this fn accepts a plan and returns an inputfilecheck

    if plan.rel_path is None:
        return InputFileCheck(
            field_name=plan.field_name,
            expected_path=Path(),
            exists=False,
            skipped=True,
            skip_reason=plan.skip_reason,
        )
    expected = module_input_dir / plan.rel_path
    check = InputFileCheck(
        field_name=plan.field_name,
        expected_path=expected,
        exists=expected.exists(),
        skip_reason=plan.skip_reason,
    )
    return check


def _check_module(
    module_schema: ModuleSchema,
    module_input_dir: Path,
) -> List[InputFileCheck]:
    # first, make plans for what checks to have based on inputs
    plans = [
        plan
        for inp in module_schema.arguments.get("inputs", [])
        for plan in plan_input_checks(inp)
    ]

    # then perform check (make expected path and check that it exsists if meant to)
    input_file_checks = [execute_check(plan, module_input_dir) for plan in plans]

    fp_plans = [
        plan
        for fp_inp in module_schema.arguments.get("fingerprint_params", [])
        for plan in plan_fp_checks(fp_inp)
    ]

    fp_file_checks = [execute_check(plan, module_input_dir) for plan in fp_plans]

    combined_file_checks = input_file_checks + fp_file_checks
    print("Number of entries in this module: ", len(combined_file_checks))
    print(
        f"this includes {len(input_file_checks)} from inputs section \n and {len(fp_file_checks)} from FP params section! "
    )

    # num_skipped = sum(1 for c in combined_file_checks if not c.skipped and c.exists)
    skipped_checks = []
    for check in combined_file_checks:
        if check.skipped is True:
            skipped_checks.append(check.field_name)
    num_skipped = len(skipped_checks)
    print("num skipped : ", num_skipped)
    for c in combined_file_checks:
        if c.skipped:
            print(f"{c.field_name} is showing as skipped.")

    for check in combined_file_checks:
        print(f"Checking {check.field_name}....")
        if check.skip_reason != "":
            print("This input was skipped in checks because:")
            print("Skip reason: ", check.skip_reason)
        else:
            print("This input wasnt skipped. Expected path is: ")
            print(check.expected_path)
    print("--")
    print("")
    return combined_file_checks  # , skipped_checks


def check_shared_data(
    discovered_module_names: List[str],
    shared_input_dir: Path,
    schemas: Dict[str, ModuleSchema],
    # registry: ModuleRegistry,
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
            schema = schemas[module_name]  # load_module_schema_from_yaml(yaml_path)
        except FileNotFoundError:
            continue

        # Collect (field_name, filename) pairs from both relevant sections.
        candidates = []

        for inp in schema.arguments.get("inputs", []):
            field_name = inp.get("name", "")
            filename = inp.get("filename")
            mount_volume = inp.get("mount", {}).get("volume", "")
            container_path = inp.get("mount", {}).get("container_path", "")
            if mount_volume == "output" or not filename:
                continue
            if container_path == "/mnt/shared_in":
                candidates.append((field_name, filename))

        for fp in schema.arguments.get("fingerprint_params", []):
            field_name = fp.get("name", "")
            filename = fp.get("filename")
            container_path = fp.get("mount", {}).get("container_path", "")
            if not filename or container_path != _SHARED_CONTAINER_PATH:
                continue
            candidates.append((field_name, filename))

        for field_name, filename in candidates:
            filenames = [filename]  # if isinstance(filename, list) else [filename]
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


def check_data(
    module_specific_input_dir: Path,
    shared_input_dir: Path,
    definitions: ModuleDefinitionSource,
) -> CheckDataResult:
    """Check data directories against expected module inputs from the registry.

    Scans module_specific_input_dir for subdirectories, matches each to known
    module names, verifies module-specific input files, and checks shared inputs
    required across all discovered modules.
    """

    # return empty result if module spec dir isn't valid path
    # (should already be checked by check_provided_paths in cli)
    if not module_specific_input_dir.exists():
        return CheckDataResult()

    # make list, dict ofschemas for known modules from registry (received from cli)
    known_modules = definitions.module_names()
    schemas = {m: definitions.get_schema(m) for m in known_modules}

    # init empty result
    full_result = CheckDataResult()

    # loop thru module-specific dir
    for entry in sorted(module_specific_input_dir.iterdir()):
        # skip if an entry isn't a sub-dir
        if not entry.is_dir():
            continue

        modules = _dir_to_module_names(entry.name, known_modules)
        if not modules:
            full_result.unrecognized_dirs.append(entry.name)
            continue

        for module_name in modules:
            # get schema
            schema = schemas[module_name]

            # perform this modules checks
            checks = _check_module(
                module_schema=schema,
                module_input_dir=entry,
            )
            # bundle into a module result obj
            module_result = CheckModuleResult(
                module_name=schema.module_name, checks=checks
            )
            # add to full results obj
            full_result.module_results.append(module_result)

    discovered_names = [r.module_name for r in full_result.module_results]
    full_result.shared_checks = check_shared_data(
        discovered_names, shared_input_dir, schemas=schemas
    )

    return full_result
