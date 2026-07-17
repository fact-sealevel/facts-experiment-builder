"""Shared path utilities for project and module discovery and path resolution."""

import os
from typing import Optional, Any

_KNOWN_MODULE_NAMES: Optional[frozenset] = None


def expand_path(path_str: Any, context: str = "") -> str:
    """
    Expand environment variables and ~ in path strings, then resolve to an absolute path.

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
