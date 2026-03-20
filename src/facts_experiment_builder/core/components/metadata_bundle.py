"""Metadata bundle helpers: clue/value dict creation, detection"""

from typing import Dict, Any


def create_metadata_bundle(clue: str, value: Any = None) -> Dict[str, Any]:
    return {"clue": clue, "value": value}


def is_metadata_value(obj: Any) -> bool:
    """Return true if obj is a metadata bundle dict (ie, it has a 'clue' key)"""
    return isinstance(obj, dict) and "clue" in obj
