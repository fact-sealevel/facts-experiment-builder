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


def _get_required_path(metadata: dict[str, Any], key: str, context: str) -> str:
    """Return a required experiment-level path value, which must be a plain string."""
    value = get_required_field(metadata, key, context)
    context_msg = f" in {context}" if context else ""
    if value is None:
        raise ValueError(
            f"Required path field '{key}' is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(value, str):
        raise ValueError(
            f"Required path field '{key}' has invalid type: expected str, got {type(value)}{context_msg}"
        )
    return value


def get_experiment_paths(metadata: dict[str, Any], context: str = "") -> dict[str, str]:
    """Extract the required experiment-level paths from metadata.

    Rules for the three required keys (`shared-input-data`,
    `module-specific-input-data`, `output-data-location`):
    - They must be present under exactly these names, as written by the
      experiment-config.yaml template. No alternative spellings are accepted.
    - Values must be plain strings. `None` (an empty field) is an error, and a
      `{"value": ...}` mapping is not unwrapped.

    `experiment-specific-input-data` is optional and handled separately by
    resolve_experiment_data_paths().

    Args:
        metadata: Experiment metadata dictionary
        context: Optional context for error messages

    Returns:
        Dictionary with keys:
        - 'shared_input_data': Path to shared input data
        - 'module_specific_input_data': Path to module-specific input data
        - 'output_data_location': Path to output data location

    Raises:
        KeyError: If a required path key is missing from metadata
        ValueError: If a required path value is None or not a string
    """
    return {
        "shared_input_data": _get_required_path(metadata, "shared-input-data", context),
        "module_specific_input_data": _get_required_path(
            metadata, "module-specific-input-data", context
        ),
        "output_data_location": _get_required_path(
            metadata, "output-data-location", context
        ),
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


@dataclass(frozen=True)
class ExperimentDataPaths:
    """Experiment-level host paths from experiment-config.yaml, expanded once per
    experiment.

    Module-level paths are built from this by resolve_module_paths().
    """

    shared_input_data: str
    # Not yet stripped of a trailing known-module dir; resolve_module_paths() does that.
    module_specific_input_base: str
    # Experiment-level output root; per-module output dirs are subdirs of this.
    output_data_location: str
    experiment_specific_input_data: str | None


def resolve_experiment_data_paths(
    metadata: dict[str, Any], context: str = "experiment config"
) -> ExperimentDataPaths:
    """Read and expand the experiment-level path keys from experiment metadata.

    The three required keys follow the rules in get_experiment_paths().
    `experiment-specific-input-data` is optional: it may be missing, empty
    (None, "", []), a string, a list (first entry used), or a `{"value": ...}`
    mapping, which is unwrapped. An empty value resolves to None.

    Args:
        metadata: Experiment metadata dictionary
        context: Context for error messages

    Returns:
        ExperimentDataPaths with expanded absolute paths

    Raises:
        KeyError: If a required path key is missing
        ValueError: If a required path value is None or invalid
    """
    experiment_paths = get_experiment_paths(metadata, context)

    raw_exp_specific = metadata.get("experiment-specific-input-data")
    if isinstance(raw_exp_specific, dict):
        raw_exp_specific = raw_exp_specific.get("value")
    experiment_specific_input = (
        expand_path(raw_exp_specific, f"{context} (experiment-specific-input-data)")
        if raw_exp_specific
        else None
    )

    shared_input_data = expand_path(
        experiment_paths["shared_input_data"],
        f"{context} (shared-input-data)",
    )
    module_specific_input_base = expand_path(
        experiment_paths["module_specific_input_data"],
        f"{context} (module-specific-input-data)",
    )
    output_data_location = expand_path(
        experiment_paths["output_data_location"],
        f"{context} (output-data-location)",
    )
    return ExperimentDataPaths(
        shared_input_data=shared_input_data,
        module_specific_input_base=module_specific_input_base,
        output_data_location=output_data_location,
        experiment_specific_input_data=experiment_specific_input,
    )


def resolve_module_paths(
    data_paths: ExperimentDataPaths,
    module_metadata: dict[str, Any],
    module_name: str,
    module_definition: ModuleSchema,
    known_module_names: list,
) -> ResolvedPaths:
    """Build one module's host paths from the experiment-level paths.

    Args:
        data_paths: Experiment-level paths from resolve_experiment_data_paths()
        module_metadata: This module's section of the experiment metadata
        module_name: Service name (e.g. 'fair-temperature', 'facts-total-wf1-global')
        module_definition: Loaded ModuleSchema for this module
        known_module_names: All module names in the experiment

    Returns:
        ResolvedPaths for this module
    """
    module_specific_input_base = data_paths.module_specific_input_base
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

    output_data_partial = data_paths.output_data_location
    # Only facts-total workflow services (names like facts-total-wf1) use a shared output
    # subdir and optional container base. Other modules are unchanged.
    is_facts_total_workflow = module_name.startswith("facts-total-")
    if is_facts_total_workflow:
        output_data_location = output_data_partial + "/facts-total"
        output_container_base = (
            module_metadata.get("_output_container_base")
            or "/mnt/total_out/facts-total"
        )
    else:
        output_data_location = output_data_partial + "/" + module_name
        output_container_base = None

    resolved_paths = ResolvedPaths(
        shared_input_data=data_paths.shared_input_data,
        module_specific_input_data=module_specific_input_data,
        output_data_location=output_data_location,
        experiment_specific_input_data=data_paths.experiment_specific_input_data,
        output_container_base=output_container_base,
    )
    return resolved_paths
