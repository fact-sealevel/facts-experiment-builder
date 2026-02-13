"""Abstract base classes and protocols for module parsers."""

import os
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any
from pathlib import Path


def expand_path(path_str: str, context: str = "") -> str:
    """
    Expand environment variables and ~ in path strings.
    
    Args:
        path_str: Path string to expand
        context: Optional context for error messages
        
    Returns:
        Expanded path string
        
    Raises:
        ValueError: If path_str is None or invalid type
    """
    if path_str is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Path string is None{context_msg}. Cannot expand None value."
        )
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


class ModuleParserProtocol(Protocol):
    """Protocol for module parsers - each module implements this."""

    def parse_from_metadata(
        self, metadata: Dict[str, Any], experiment_dir: Path
    ) -> Any:
        """Parse metadata and return module instance."""
        pass


class ModuleParserABC(ABC):
    """Abstract base class for module parsers."""

    @abstractmethod
    def parse_from_metadata(
        self, metadata: Dict[str, Any], experiment_dir: Path
    ) -> Any:
        """Parse metadata and return module instance."""
        pass

    @abstractmethod
    def get_module_type(self) -> str:
        """Return module type/name identifier (eg. 'fair', 'bamber19-icesheets'...)."""
        pass

