# """Create modules from experiment metadata."""

# from pathlib import Path
# from typing import Dict, Any, Optional, List

# from facts_experiment_builder.adapters.experiment_metadata_to_service_spec import (
#     build_module_service_spec,
# )
# from facts_experiment_builder.core.module.module_schema import ModuleSchema

# from facts_experiment_builder.infra.experiment_loader import load_experiment_metadata


# def create_module_service_spec_from_metadata(
#     experiment_dir: Path,
#     module_name: str,
#     experiment_metadata: Dict,
#     module_definition: ModuleSchema,
#     known_module_names: List,
#     module_type: Optional[str] = None,
#     metadata: Optional[Dict[str, Any]] = None,
# ):
#     """
#     Create a single module service spec from experiment metadata.

#     Args:
#         experiment_dir: Path to dir containing experiment-config.yaml
#         module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets')
#         module_type: Optional category (e.g. 'temperature_module', 'sealevel_module')
#         metadata: Optional pre-loaded metadata. If provided, skips loading from disk.
#         module_yaml_path: Optional path to module YAML (e.g. for facts-total workflow services)

#     Returns:
#         ModuleServiceSpec
#     """

#     # metadata_path = Path(
#     #     experiment_dir, "experiment-config.yaml"
#     # )  # this should now come from comopse
#     # if metadata is None:
#     #     metadata = load_experiment_metadata(metadata_path)

#     try:
#         return build_module_service_spec(
#             metadata=metadata,
#             known_module_names=known_module_names,
#             module_definition=module_definition,
#             module_name=module_name,
#             module_type=module_type,
#         )
#     except Exception as e:
#         error_msg = str(e)
#         print(f"Error creating module from metadata: {error_msg}")
#         raise e
