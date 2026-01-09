"""Abstract base classes and protocols for module parsers."""

import os
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any
from pathlib import Path


def expand_path(path_str: str) -> str:
    """Expand environment variables and ~ in path strings."""
    if isinstance(path_str, list):
        path_str = path_str[0] if path_str else ""
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

