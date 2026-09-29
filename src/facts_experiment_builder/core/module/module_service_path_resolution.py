"""Resolve experiment-level and module-level host paths from experiment metadata."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from facts_experiment_builder.core.typed_path import (
    _MODULE_SPECIFIC_CONTAINER_PATH,
    _SHARED_CONTAINER_PATH,
)
from facts_experiment_builder.core.module.arg_specs import MountSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema


def is_shared_input(mount: MountSpec | None) -> bool:
    """Determine if an input field is a shared input (shared across modules).

    Shared inputs include location files and fingerprint directories.
    These should be resolved using 'shared-input-data' base path.

    Args:
        field_name: Name of the input field

    Returns:
        True if field is a shared input, False if module-specific
    """
    if mount is None:
        raise ValueError("Expected a mount with 'container_path', got None")

    container_path = mount.container_path
    if container_path == _SHARED_CONTAINER_PATH:
        return True
    elif container_path == _MODULE_SPECIFIC_CONTAINER_PATH:
        return False
    else:
        raise ValueError(
            f"Expected one of '{_SHARED_CONTAINER_PATH}' or '{_MODULE_SPECIFIC_CONTAINER_PATH}'."
            f"Received '{container_path}'."
        )


def resolve_input_path(
    field_name: str,
    field_value: Any,
    mount: MountSpec | None,
    shared_input_data: str,
    module_specific_input_data: str,
    module_name: str = "",
    context: str = "",
):
    """Resolve an input file path based on whether it's a general or module-specific
    input.

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

    if mount is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Input field '{field_name}' has no 'mount' declared in the module schema"
            f"{context_msg}. This field is present in metadata but not declared as an "
            f"input in the module YAML."
        )

    is_general = is_shared_input(mount)

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

        resolved_path = os.path.join(module_specific_input_data, actual_value)

    return os.path.normpath(resolved_path)


def resolve_output_path(field_value: Any, output_data_location: str, context: str = ""):
    """Resolve an output file path using the output-data-location base path.

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


def get_required_field(
    metadata: dict[str, Any], field_name: str, context: str = ""
) -> Any:
    """Get a required field from metadata, raising an error if missing.

    Args:
        metadata: Metadata dictionary
        field_name: Name of the field to extract
        context: Optional context for error message (e.g., module name)

    Returns:
        Field value

    Raises:
        KeyError: If field is missing
    """
    if field_name not in metadata:
        context_msg = f" in {context}" if context else ""
        raise KeyError(
            f"Required field '{field_name}' is missing from metadata{context_msg}. Instead, saw {metadata.keys()}"
        )
    return metadata[field_name]


def get_required_field_with_alternatives(
    metadata: dict[str, Any],
    primary_field: str,
    alternative_fields: list[str],
    context: str = "",
) -> Any:
    """Get a required field, trying primary first, then alternatives.

    Args:
        metadata: Metadata dictionary
        primary_field: Primary field name to try first
        alternative_fields: List of alternative field names to try
        context: Optional context for error message

    Returns:
        Field value from first found field

    Raises:
        KeyError: If none of the fields are present
    """
    # Try primary field first
    if primary_field in metadata:
        return metadata[primary_field]

    # Try alternatives
    for alt_field in alternative_fields:
        if alt_field in metadata:
            return metadata[alt_field]

    # None found
    # all_fields = [primary_field] + alternative_fields
    context_msg = f" in {context}" if context else ""
    raise KeyError(
        f"Required field '{primary_field}' (or alternatives: {', '.join(alternative_fields)}) "
        f"is missing from metadata{context_msg}"
    )


def get_experiment_paths(metadata: dict[str, Any], context: str = "") -> dict[str, str]:
    """Extract experiment-level paths from metadata.

    Args:
        metadata: Experiment metadata dictionary
        context: Optional context for error messages

    Returns:
        Dictionary with keys:
        - 'shared_input_data': Path to shared input data
        - 'module_specific_input_data': Path to module-specific input data
        - 'output_data_location': Path to output data location

    Raises:
        KeyError: If required paths are missing from metadata
        ValueError: If path values are None or invalid
    """
    shared_input_data = get_required_field_with_alternatives(
        metadata, "shared-input-data", ["shared_input_data"], context
    )
    if shared_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'shared-input-data' (or 'shared_input_data') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(shared_input_data, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'shared-input-data' has invalid type: expected str, got {type(shared_input_data)}{context_msg}"
        )

    module_specific_input_data = get_required_field_with_alternatives(
        metadata, "module-specific-input-data", ["module_specific_input_data"], context
    )
    if module_specific_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'module-specific-input-data' (or 'module_specific_input_data') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(module_specific_input_data, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'module-specific-input-data' has invalid type: expected str, got {type(module_specific_input_data)}{context_msg}"
        )

    output_data_location = get_required_field_with_alternatives(
        metadata,
        "output-data-location",
        ["output_data_location", "output-path", "output_path"],
        context,
    )
    if output_data_location is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'output-data-location' (or alternatives: 'output_data_location', 'output-path', 'output_path') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(output_data_location, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'output-data-location' has invalid type: expected str, got {type(output_data_location)}{context_msg}"
        )

    return {
        "shared_input_data": shared_input_data,
        "module_specific_input_data": module_specific_input_data,
        "output_data_location": output_data_location,
    }


@dataclass
class ResolvedPaths:
    shared_input_data: str
    module_specific_input_data: str
    experiment_specific_input_data: str | None
    output_data_location: str
    output_container_base: str | None = None


def expand_path(path_str: Any, context: str = "") -> str:
    """Expand environment variables and ~ in path strings, then resolve to an absolute
    path.

    Resolving to absolute ensures all downstream path operations (volume mounts,
    container path computation) work correctly regardless of the working directory
    FEB is invoked from. Users can provide either absolute paths or paths relative
    to their working directory in the experiment config.

    Args:
        path_str: Path string to expand (or list with first element used)
        context: Optional context for error messages

    Returns:
        Absolute path string

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
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path_str)))


def resolve_experiment_paths(
    metadata: dict[str, Any],
    module_name_str: str,
    known_module_names: list,
    module_name: str,
    module_definition: ModuleSchema,
) -> ResolvedPaths:  # tuple[ModuleInputPaths, ModuleOutputPaths, Union[str, Path]]:
    # module_name = module_definition.module_name
    experiment_paths = get_experiment_paths(metadata, module_name_str)
    module_metadata = get_required_field(metadata, module_name, module_name_str)

    raw_exp_specific = metadata.get("experiment-specific-input-data")
    if isinstance(raw_exp_specific, dict):
        raw_exp_specific = raw_exp_specific.get("value")
    experiment_specific_input = (
        expand_path(
            raw_exp_specific, f"{module_name_str} (experiment-specific-input-data)"
        )
        if raw_exp_specific
        else None
    )

    shared_input_data = expand_path(
        experiment_paths["shared_input_data"],
        f"{module_name_str} (shared-input-data)",
    )

    module_specific_input_base = expand_path(
        experiment_paths["module_specific_input_data"],
        f"{module_name_str} (module-specific-input-data)",
    )
    # If metadata points at a specific module's dir (e.g. .../fair-temperature), use parent as base
    # so volume host path is always base + current module's suffix only (never another module's name).
    if (
        Path(module_specific_input_base).name in known_module_names
    ):  # registry.module_names():
        module_specific_input_base = str(Path(module_specific_input_base).parent)
    # Module-specific input dir: driven by input_dir_name in module YAML (e.g. "ipccar5" for both
    # ipccar5-glaciers and ipccar5-icesheets). Falls back to module_definition.module_name so that
    # per-workflow service names (e.g. extremesealevel-pointsoverthreshold-wf1) resolve to the base
    # module's dir automatically.
    module_specific_input_path_suffix = module_definition.input_dir_name  # ()
    module_specific_input_data = (
        module_specific_input_base + "/" + module_specific_input_path_suffix
    )

    output_data_partial = expand_path(
        experiment_paths["output_data_location"],
        f"{module_name_str} (output-data-location)",
    )
    # Only facts-total workflow services (names like facts-total-wf1) use a shared output
    # subdir and optional container base. Other modules are unchanged.
    is_facts_total_workflow = module_name.startswith("facts-total-")
    if is_facts_total_workflow:
        output_data_location = output_data_partial + "/facts-total"
        if not Path(output_data_location).exists():
            os.makedirs(output_data_location, exist_ok=True)

        output_container_base = (
            module_metadata.get("_output_container_base")
            or "/mnt/total_out/facts-total"
        )
    else:
        output_data_location = output_data_partial + "/" + module_name
        if not Path(output_data_location).exists():
            os.makedirs(output_data_location, exist_ok=True)
        output_container_base = None

    resolved_paths = ResolvedPaths(
        shared_input_data=shared_input_data,
        module_specific_input_data=module_specific_input_data,
        output_data_location=output_data_location,
        experiment_specific_input_data=experiment_specific_input,
        output_container_base=output_container_base,
    )
    return resolved_paths
