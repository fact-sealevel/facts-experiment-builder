"""Filesystem helpers for module output directories."""

import os
from pathlib import Path


def ensure_module_output_dir(path: str) -> None:
    """Create the module output directory on disk if it does not exist."""
    if not Path(path).exists():
        os.makedirs(path, exist_ok=True)
