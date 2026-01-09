"""Utility functions for parsers to extract required fields from metadata."""

from typing import Dict, Any, List, Optional


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
            f"Required field '{field_name}' is missing from metadata{context_msg}"
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

