from pathlib import Path


import pytest

_REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "facts-module-registry"
pytestmark = pytest.mark.skipif(
    not _REGISTRY_DIR.exists(),
    reason="facts-module-registry not present — clone it to run registry tests",
)
