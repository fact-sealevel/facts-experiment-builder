"""Shared path utilities for project and module discovery and path resolution."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


def expand_path(path_str: Any, context: str = "") -> str:
    """
    Expand environment variables and ~ in path strings.

    Args:
        path_str: Path string to expand (or list with first element used)
        context: Optional context for error messages

    Returns:
        Expanded path string

    Raises:
        ValueError: If path_str is None or invalid type
    """
    if path_str is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(f"Path string is None{context_msg}. Cannot expand None value.")
    if isinstance(path_str, list):
        path_str = path_str[0] if path_str else ""
        if not path_str:
            context_msg = f" in {context}" if context else ""
            raise ValueError(
                f"Path string is empty list{context_msg}. Cannot expand empty path."
            )
    if not isinstance(path_str, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Path string has invalid type: expected str, got {type(path_str)}{context_msg}"
        )
    return os.path.expandvars(os.path.expanduser(path_str))


def _resolve_module_input_dir(module_specific_input_dir: str, module_name: str) -> str:
    """Resolve the effective module input directory from base path and module name."""
    if not module_name or not module_specific_input_dir:
        return module_specific_input_dir
    try:
        base_path = Path(module_specific_input_dir)
    except TypeError as e:
        raise ValueError(
            f"Cannot create Path from module_specific_input_dir for {module_name}: "
            f"module_specific_input_dir={module_specific_input_dir!r}, type={type(module_specific_input_dir)}"
        ) from e
    if base_path.name == module_name:
        return module_specific_input_dir
    # Multi-command module: path already points at shared dir (e.g. .../ipccar5); do not append module_name.
    if base_path.name and module_name.startswith(base_path.name + "-"):
        return module_specific_input_dir
    if base_path.name:
        return str(base_path.parent / module_name)
    return os.path.join(module_specific_input_dir, module_name)


ModuleOutputType = Literal["local", "global", "total", "esl"]


@dataclass(frozen=True)
class ModuleInputPaths:
    """Input paths for a module: module-specific and general dirs, plus resolved input_dir."""

    input_dir: str
    module_specific_input_dir: str
    general_input_dir: str


@dataclass(frozen=True)
class ModuleOutputPaths:
    """Output paths for a module."""

    output_dir: str
    output_type: ModuleOutputType


def build_module_input_paths(
    *,
    module_specific_input_dir: str = "",
    general_input_dir: str = "",
    module_name: str = "",
) -> ModuleInputPaths:
    """Build and validate ModuleInputPaths. Raises ValueError if invalid."""
    if module_specific_input_dir is None:
        raise ValueError(
            f"module_specific_input_dir is None when building paths for {module_name}."
        )
    if module_specific_input_dir != "" and not isinstance(
        module_specific_input_dir, str
    ):
        raise ValueError(
            f"module_specific_input_dir has invalid type for {module_name}: expected str, got {type(module_specific_input_dir)}"
        )
    if general_input_dir is None:
        raise ValueError(
            f"general_input_dir is None when building paths for {module_name}."
        )
    if general_input_dir != "" and not isinstance(general_input_dir, str):
        raise ValueError(
            f"general_input_dir has invalid type for {module_name}: expected str, got {type(general_input_dir)}"
        )
    ms = module_specific_input_dir or ""
    gen = general_input_dir or ""
    input_dir = _resolve_module_input_dir(ms, module_name)
    return ModuleInputPaths(
        input_dir=input_dir,
        module_specific_input_dir=ms,
        general_input_dir=gen,
    )


def build_module_output_paths(
    output_dir: str, output_type: ModuleOutputType, module_name: str = ""
) -> ModuleOutputPaths:
    """Build and validate ModuleOutputPaths. Raises ValueError if invalid."""
    if output_dir is None:
        raise ValueError(
            f"output_dir is None when building paths for {module_name}. "
            "This usually means 'output-data-location' path is None in metadata."
        )
    if not isinstance(output_dir, str):
        raise ValueError(
            f"output_dir has invalid type for {module_name}: expected str, got {type(output_dir)}"
        )
    return ModuleOutputPaths(output_dir=output_dir, output_type=output_type)


def find_project_root(start_path: Path = None) -> Path:
    """
    Find the project root by looking for pyproject.toml.

    Searches upward from start_path (or cwd). If not found, falls back to
    searching from this file's directory so setup remains robust when run
    from arbitrary cwds.

    Args:
        start_path: Path to start searching from (defaults to current working directory)

    Returns:
        Path to project root (directory containing pyproject.toml)

    Raises:
        FileNotFoundError: If pyproject.toml is not found
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path
    while current != current.parent:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return current
        current = current.parent

    # Fallback: search from this file's location
    script_path = Path(__file__).resolve().parent
    current = script_path
    while current != current.parent:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return current
        current = current.parent

    raise FileNotFoundError(
        f"Could not find pyproject.toml starting from {start_path}. "
        "Please run from within the project directory."
    )


def is_general_input(field_name: str) -> bool:
    """
    Determine if an input field is a general input (shared across modules).

    General inputs include location files and fingerprint directories.
    These should be resolved using 'general-input-data' base path.

    Args:
        field_name: Name of the input field

    Returns:
        True if field is a general input, False if module-specific
    """
    field_lower = field_name.lower()
    general_patterns = ["location", "fingerprint", "fp"]
    return any(pattern in field_lower for pattern in general_patterns)


def resolve_input_path(
    field_name: str,
    field_value: Any,
    general_input_data: str,
    module_specific_input_data: str,
    module_name: str = "",
    context: str = "",
):
    """
    Resolve an input file path based on whether it's a general or module-specific input.

    General inputs (location_file, fingerprint_dir, etc.) use 'general-input-data'.
    Module-specific inputs use 'module-specific-input-data/{module_name}/{file_name}'.

    Args:
        field_name: Name of the input field
        field_value: Value from metadata (can be string path or dict with 'value' key)
        general_input_data: Base path for general inputs
        module_specific_input_data: Base path for module-specific inputs
        module_name: Name of the module (required for module-specific inputs)
        context: Optional context for error messages

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If field_value is invalid or path cannot be resolved
    """
    if isinstance(field_value, dict):
        actual_value = field_value.get("value", "")
    elif isinstance(field_value, str):
        actual_value = field_value
    else:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Invalid field value type for '{field_name}': expected str or dict, got {type(field_value)}{context_msg}"
        )

    if not actual_value or (
        isinstance(actual_value, str) and actual_value.strip() == ""
    ):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Empty or missing value for input field '{field_name}'{context_msg}"
        )

    is_general = is_general_input(field_name)

    if os.path.isabs(actual_value):
        return actual_value

    if general_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"general_input_data is None when resolving input path for '{field_name}'{context_msg}. "
            f"This usually means 'general-input-data' path is None in metadata."
        )
    if module_specific_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"module_specific_input_data is None when resolving input path for '{field_name}'{context_msg}. "
            f"This usually means 'module-specific-input-data' path is None in metadata."
        )

    if is_general:
        base_path = general_input_data
        resolved_path = os.path.join(base_path, actual_value)
    else:
        if not module_name:
            context_msg = f" in {context}" if context else ""
            raise ValueError(
                f"Module name is required for module-specific input '{field_name}'{context_msg}"
            )
        try:
            module_specific_path = Path(module_specific_input_data)
        except TypeError as e:
            context_msg = f" in {context}" if context else ""
            raise ValueError(
                f"Cannot create Path from module_specific_input_data for '{field_name}': "
                f"module_specific_input_data={module_specific_input_data}, type={type(module_specific_input_data)}{context_msg}"
            ) from e
        if module_specific_path.name == module_name:
            base_path = module_specific_input_data
        elif module_specific_path.name and module_name.startswith(
            module_specific_path.name + "-"
        ):
            # Multi-command module sharing one dir (e.g. ipccar5 for ipccar5-glaciers/ipccar5-icesheets).
            # Files sit directly under module_specific_input_data; do not append module_name.
            base_path = module_specific_input_data
        else:
            if module_specific_path.name in [
                "fair-temperature",
                "fair-climate",
                "bamber19-icesheets",
                "deconto21-ais",
                "ipccar5-glaciers",
                "ipccar5-icesheets",
                "larmip-ais",
                "fittedismip-gris",
                "tlm-sterodynamics",
                "ssp-landwaterstorage",
                "kopp14-verticallandmotion",
                "nzinsargps-verticallandmotion",
            ]:
                base_path = str(module_specific_path.parent / module_name)
            else:
                base_path = os.path.join(module_specific_input_data, module_name)
        resolved_path = os.path.join(base_path, actual_value)

    return os.path.normpath(resolved_path)


def resolve_output_path(field_value: Any, output_data_location: str, context: str = ""):
    """
    Resolve an output file path using the output-data-location base path.

    Args:
        field_value: Value from metadata (can be string path or dict with 'value' key)
        output_data_location: Base path for outputs
        context: Optional context for error messages

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If field_value is invalid or path cannot be resolved
    """

    if output_data_location is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"output_data_location is None when resolving output path{context_msg}. "
            f"This usually means 'output-data-location' path is None in metadata."
        )
    if not isinstance(output_data_location, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"output_data_location has invalid type: expected str, got {type(output_data_location)}{context_msg}"
        )

    if isinstance(field_value, dict):
        actual_value = field_value.get("value", "")
    elif isinstance(field_value, str):
        actual_value = field_value
    else:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Invalid field value type for output: expected str or dict, got {type(field_value)}{context_msg}"
        )

    if not actual_value or (
        isinstance(actual_value, str) and actual_value.strip() == ""
    ):
        context_msg = f" in {context}" if context else ""
        raise ValueError(f"Empty or missing value for output field{context_msg}")

    if os.path.isabs(actual_value):
        return actual_value
    resolved_path = os.path.join(output_data_location, actual_value)

    returned_resolved_path = os.path.normpath(resolved_path)
    return returned_resolved_path
