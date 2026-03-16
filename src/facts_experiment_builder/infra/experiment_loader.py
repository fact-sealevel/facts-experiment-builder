import yaml
from pathlib import Path
from typing import Dict, Any


def load_experiment_metadata(metadata_path: Path) -> Dict[str, Any]:
    """Load experiment metadata from YAML file."""
    with open(metadata_path) as f:
        return yaml.safe_load(f)
