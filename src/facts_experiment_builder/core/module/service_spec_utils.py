from typing import Set, Any, Dict, Optional, List
import os

from facts_experiment_builder.core.typed_path import (
    _MODULE_SPECIFIC_CONTAINER_PATH,
    _SHARED_CONTAINER_PATH,
)


def _input_spec_by_key(module_definition: Any) -> Dict[str, dict]:
    result = {}
    for arg_spec in module_definition.arguments.get("inputs", []):
        source = arg_spec.get("source", "")
        if "." in source:
            result[source.split(".")[-1]] = arg_spec
    return result


def declares_input(module_definition: Any, field_name: str) -> bool:
    """Return True if the module's schema declares an input sourced from
    module_inputs.inputs.<field_name>."""
    return field_name in _input_spec_by_key(module_definition)


def _dir_input_keys(module_definition: Any) -> Set[str]:
    """Return set of input field names declared as directory paths (type: 'dir') in the
    module YAML."""
    keys: Set[str] = set()
    for arg_spec in module_definition.arguments.get("inputs", []):
        if arg_spec.get("type") != "dir":
            continue
        source = arg_spec.get("source", "")
        if "." in source:
            keys.add(source.split(".")[-1])
    return keys


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


def is_shared_input(mount: Optional[dict]) -> bool:
    """Determine if an input field is a shared input (shared across modules).

    Shared inputs include location files and fingerprint directories.
    These should be resolved using 'shared-input-data' base path.

    Args:
        field_name: Name of the input field

    Returns:
        True if field is a shared input, False if module-specific
    """
    if not isinstance(mount, dict):
        raise ValueError(
            f"Expected mount to be a dict with 'container_path', got {type(mount)}"
        )

    container_path = mount.get("container_path")
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
    mount: Optional[Dict],
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
    metadata: Dict[str, Any], field_name: str, context: str = ""
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
    metadata: Dict[str, Any],
    primary_field: str,
    alternative_fields: List[str],
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


def get_experiment_paths(metadata: Dict[str, Any], context: str = "") -> Dict[str, str]:
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
