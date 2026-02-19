"""Create modules from experiment metadata."""

from pathlib import Path
from typing import Dict, Any, Optional

from facts_experiment_builder.adapters.experiment_metadata_to_service_spec import build_module_service_spec

from facts_experiment_builder.infra.module_loader import load_experiment_metadata

def create_module_from_metadata(
    metadata_path: Path,
    module_name: str,
    module_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ):
    """
    Create a single module from experiment metadata.

    Args:
        metadata_path: Path to experiment-metadata.yml
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets')
        module_type: Optional category (e.g. 'temperature_module', 'sealevel_module')
        metadata: Optional pre-loaded metadata (if provided, metadata_path is used only for experiment_dir)

    Returns:
        ModuleServiceSpec instance
    """
    if metadata is None:
        metadata = load_experiment_metadata(metadata_path)
    experiment_dir = metadata_path.parent

    try:
        return build_module_service_spec(
            metadata,
            experiment_dir,
            module_name=module_name,
            module_type=module_type,
        )
    except Exception as e:
        error_msg = str(e)
        print(f"Error creating module from metadata: {error_msg}")
        raise e


