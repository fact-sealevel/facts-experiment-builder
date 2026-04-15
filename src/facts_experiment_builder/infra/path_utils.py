"""Shared path utilities for project and module discovery and path resolution."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

_KNOWN_MODULE_NAMES: Optional[frozenset] = None


def _registry_module_names() -> frozenset:
    global _KNOWN_MODULE_NAMES
    if _KNOWN_MODULE_NAMES is None:
        from facts_experiment_builder.core.registry.module_registry import (
            ModuleRegistry,
        )

        _KNOWN_MODULE_NAMES = frozenset(ModuleRegistry.default().list_modules())
    return _KNOWN_MODULE_NAMES


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
    shared_input_dir: str


@dataclass(frozen=True)
class ModuleOutputPaths:
    """Output paths for a module."""

    output_dir: str
    output_type: ModuleOutputType


def build_module_input_paths(
    *,
    module_specific_input_dir: str = "",
    shared_input_dir: str = "",
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
    if shared_input_dir is None:
        raise ValueError(
            f"shared_input_dir is None when building paths for {module_name}."
        )
    if shared_input_dir != "" and not isinstance(shared_input_dir, str):
        raise ValueError(
            f"shared_input_dir has invalid type for {module_name}: expected str, got {type(shared_input_dir)}"
        )
    ms = module_specific_input_dir or ""
    gen = shared_input_dir or ""
    input_dir = _resolve_module_input_dir(ms, module_name)
    return ModuleInputPaths(
        input_dir=input_dir,
        module_specific_input_dir=ms,
        shared_input_dir=gen,
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


def is_shared_input(field_name: str) -> bool:
    """
    Determine if an input field is a shared input (shared across modules).

    Shared inputs include location files and fingerprint directories.
    These should be resolved using 'shared-input-data' base path.

    Args:
        field_name: Name of the input field

    Returns:
        True if field is a shared input, False if module-specific
    """
    field_lower = field_name.lower()
    general_patterns = ["location", "fingerprint", "fp"]
    return any(pattern in field_lower for pattern in general_patterns)


def resolve_input_path(
    field_name: str,
    field_value: Any,
    shared_input_data: str,
    module_specific_input_data: str,
    module_name: str = "",
    context: str = "",
):
    """
    Resolve an input file path based on whether it's a general or module-specific input.

    Shared inputs (location_file, fingerprint_dir, etc.) use 'shared-input-data'.
    Module-specific inputs use 'module-specific-input-data/{module_name}/{file_name}'.

    Args:
        field_name: Name of the input field
        field_value: Value from metadata (can be string path or dict with 'value' key)
        shared_input_data: Base path for shared inputs
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

    is_general = is_shared_input(field_name)

    if os.path.isabs(actual_value):
        return actual_value

    if shared_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"shared_input_data is None when resolving input path for '{field_name}'{context_msg}. "
            f"This usually means 'shared-input-data' path is None in metadata."
        )
    if module_specific_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"module_specific_input_data is None when resolving input path for '{field_name}'{context_msg}. "
            f"This usually means 'module-specific-input-data' path is None in metadata."
        )

    if is_general:
        base_path = shared_input_data
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
            if module_specific_path.name in _registry_module_names():
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
