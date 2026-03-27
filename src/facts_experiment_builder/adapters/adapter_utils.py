"""Manifest and metadata parsing helpers for adapters. Path resolution lives in utils.path_utils."""

from typing import Dict, Any, List

__all__ = [
    "get_required_field",
    "get_required_field_with_alternatives",
    "get_experiment_paths",
]


def get_required_field(
    metadata: Dict[str, Any], field_name: str, context: str = ""
) -> Any:
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
    context: str = "",
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
    # all_fields = [primary_field] + alternative_fields
    context_msg = f" in {context}" if context else ""
    raise KeyError(
        f"Required field '{primary_field}' (or alternatives: {', '.join(alternative_fields)}) "
        f"is missing from metadata{context_msg}"
    )


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
        "general_input_data": general_input_data,
        "module_specific_input_data": module_specific_input_data,
        "output_data_location": output_data_location,
    }
