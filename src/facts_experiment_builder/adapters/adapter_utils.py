"""Utility functions for parsers to extract required fields from metadata."""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path


def get_required_field(metadata: Dict[str, Any], field_name: str, context: str = "") -> Any:
    """
    Get a required field from metadata, raising an error if missing.
    
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
    context: str = ""
) -> Any:
    """
    Get a required field, trying primary first, then alternatives.
    
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
    all_fields = [primary_field] + alternative_fields
    context_msg = f" in {context}" if context else ""
    raise KeyError(
        f"Required field '{primary_field}' (or alternatives: {', '.join(alternative_fields)}) "
        f"is missing from metadata{context_msg}"
    )


def get_required_nested_field(
    metadata: Dict[str, Any],
    field_path: List[str],
    context: str = ""
) -> Any:
    """
    Get a required field from nested dictionary structure.
    
    Args:
        metadata: Metadata dictionary
        field_path: List of keys to traverse (e.g., ["v2-output-files", "fair"])
        context: Optional context for error message
    
    Returns:
        Field value
    
    Raises:
        KeyError: If any part of the path is missing
    """
    current = metadata
    path_str = " -> ".join(field_path)
    
    for key in field_path:
        if not isinstance(current, dict):
            context_msg = f" in {context}" if context else ""
            raise KeyError(
                f"Path '{path_str}' is invalid: '{key}' is not a dictionary{context_msg}"
            )
        if key not in current:
            context_msg = f" in {context}" if context else ""
            raise KeyError(
                f"Required field '{key}' missing in path '{path_str}'{context_msg}"
            )
        current = current[key]
    
    return current


def get_required_list_item(
    value: List[Any],
    index: int,
    field_name: str,
    context: str = ""
) -> Any:
    """
    Get a required item from a list, raising error if index is out of range.
    
    Args:
        value: List to index into
        index: Index to access
        field_name: Name of the field (for error message)
        context: Optional context for error message
    
    Returns:
        List item at index
    
    Raises:
        IndexError: If index is out of range
    """
    if index >= len(value):
        context_msg = f" in {context}" if context else ""
        raise IndexError(
            f"Required item at index {index} missing from '{field_name}' list "
            f"(list has {len(value)} items){context_msg}"
        )
    return value[index]


def get_required_field_nested_or_top(
    metadata: Dict[str, Any],
    field_name: str,
    nested_key: str,
    context: str = ""
) -> Any:
    """
    Get a required field, checking nested location first, then top level.
    
    Args:
        metadata: Metadata dictionary
        field_name: Name of the field to extract
        nested_key: Key of the nested dict to check first (e.g., "fair-inputs")
        context: Optional context for error message
    
    Returns:
        Field value from nested location if found, otherwise from top level
    
    Raises:
        KeyError: If field is missing from both locations
    """
    # Check nested location first
    if nested_key in metadata and isinstance(metadata[nested_key], dict):
        nested_dict = metadata[nested_key]
        if field_name in nested_dict:
            return nested_dict[field_name]
    
    # Fall back to top level
    if field_name in metadata:
        return metadata[field_name]
    
    # Not found in either location
    context_msg = f" in {context}" if context else ""
    raise KeyError(
        f"Required field '{field_name}' is missing from metadata "
        f"(checked in '{nested_key}' and at top level){context_msg}"
    )


def parse_manifest_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the experiment manifest from metadata.
    
    This extracts which modules are specified in the experiment.
    
    Args:
        metadata: Loaded metadata dictionary
        
    Returns:
        Dictionary with module specifications
    """
    manifest = {
        "temperature_module": metadata.get("temperature_module"),
        "sealevel_modules": metadata.get("sealevel_modules", []),
        "framework_modules": metadata.get("framework_modules", []),
        "esl_modules": metadata.get("esl_modules", []),
    } #TODO change this if we want to not rely on module types
    
    # Normalize sealevel_modules to list
    if isinstance(manifest["sealevel_modules"], str):
        manifest["sealevel_modules"] = [manifest["sealevel_modules"]]
    
    return manifest


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
    general_patterns = ['location', 'fingerprint', 'fp']
    
    # Check if field name contains any general input pattern
    return any(pattern in field_lower for pattern in general_patterns)


def resolve_input_path(
    field_name: str,
    field_value: Any,
    general_input_data: str,
    module_specific_input_data: str,
    module_name: str = "",
    context: str = ""
) -> str:
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
    # Extract actual value if it's a metadata bundle dict
    if isinstance(field_value, dict):
        # Handle metadata bundle format: {"clue": "...", "value": "..."}
        actual_value = field_value.get("value", "")
    elif isinstance(field_value, str):
        actual_value = field_value
    else:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Invalid field value type for '{field_name}': expected str or dict, got {type(field_value)}{context_msg}"
        )
    
    if not actual_value or (isinstance(actual_value, str) and actual_value.strip() == ""):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Empty or missing value for input field '{field_name}'{context_msg}"
        )
    
    # Determine base path based on field type
    is_general = is_general_input(field_name)
    
    # Handle absolute vs relative paths
    if os.path.isabs(actual_value):
        # If already absolute, return as-is
        return actual_value
    
    # Validate base paths are not None
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
    
    # Relative path - resolve based on input type
    if is_general:
        # General inputs: {general_input_data}/{file_name}
        base_path = general_input_data
        resolved_path = os.path.join(base_path, actual_value)
    else:
        # Module-specific inputs: {module_specific_input_data}/{module_name}/{file_name}
        # But check if module_name is already in the path to avoid duplicates
        if not module_name:
            context_msg = f" in {context}" if context else ""
            raise ValueError(
                f"Module name is required for module-specific input '{field_name}'{context_msg}"
            )
        # Check if module name is already the last component of module_specific_input_data
        try:
            module_specific_path = Path(module_specific_input_data)
        except TypeError as e:
            context_msg = f" in {context}" if context else ""
            raise ValueError(
                f"Cannot create Path from module_specific_input_data for '{field_name}': "
                f"module_specific_input_data={module_specific_input_data}, type={type(module_specific_input_data)}{context_msg}"
            ) from e
        if module_specific_path.name == module_name:
            # Module name already in path, don't add it again
            base_path = module_specific_input_data
        else:
            # Check if path ends with a different module name (common mistake in metadata)
            # If so, replace it with the correct module name
            # Otherwise, add module name to create module-specific subdirectory
            if module_specific_path.name in ["fair-temperature", "fair-climate", "bamber19-icesheets", 
                                             "deconto21-ais", "ipccar5-glaciers", "ipccar5-icesheets",
                                             "larmip-ais", "fittedismip-gris", "tlm-sterodynamics",
                                             "ssp-landwaterstorage", "kopp14-verticallandmotion",
                                             "nzinsargps-verticallandmotion"]:
                # Path ends with a module name, replace it with current module name
                base_path = str(module_specific_path.parent / module_name)
            else:
                # Add module name to create module-specific subdirectory
                base_path = os.path.join(module_specific_input_data, module_name)
        resolved_path = os.path.join(base_path, actual_value)
    
    return os.path.normpath(resolved_path)


def resolve_output_path(
    field_value: Any,
    output_data_location: str,
    context: str = ""
) -> str:
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
    # Validate output_data_location is not None
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
    
    # Extract actual value if it's a metadata bundle dict
    if isinstance(field_value, dict):
        actual_value = field_value.get("value", "")
    elif isinstance(field_value, str):
        actual_value = field_value
    else:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Invalid field value type for output: expected str or dict, got {type(field_value)}{context_msg}"
        )
    
    if not actual_value or (isinstance(actual_value, str) and actual_value.strip() == ""):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Empty or missing value for output field{context_msg}"
        )
    
    # Handle absolute vs relative paths
    if os.path.isabs(actual_value):
        return actual_value
    else:
        resolved_path = os.path.join(output_data_location, actual_value)
        return os.path.normpath(resolved_path)


def get_experiment_paths(metadata: Dict[str, Any], context: str = "") -> Dict[str, str]:
    """
    Extract experiment-level paths from metadata.
    
    Args:
        metadata: Experiment metadata dictionary
        context: Optional context for error messages
        
    Returns:
        Dictionary with keys:
        - 'general_input_data': Path to general input data
        - 'module_specific_input_data': Path to module-specific input data
        - 'output_data_location': Path to output data location
        
    Raises:
        KeyError: If required paths are missing from metadata
        ValueError: If path values are None or invalid
    """
    general_input_data = get_required_field_with_alternatives(
        metadata, "general-input-data", ["general_input_data"], context
    )
    if general_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'general-input-data' (or 'general_input_data') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(general_input_data, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'general-input-data' has invalid type: expected str, got {type(general_input_data)}{context_msg}"
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
        metadata, "output-data-location", ["output_data_location", "output-path", "output_path"], context
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
        "general_input_data": general_input_data,
        "module_specific_input_data": module_specific_input_data,
        "output_data_location": output_data_location,
    }

