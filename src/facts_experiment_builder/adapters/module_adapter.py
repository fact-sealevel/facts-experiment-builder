"""Factory and utilities for creating modules from experiment metadata."""

import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from facts_experiment_builder.adapters.abstract_adapter import (
    ModuleParserABC,
)
from facts_experiment_builder.adapters.generic_module_parser import (
    GenericModuleParser,
)


def load_metadata(metadata_path: Path) -> Dict[str, Any]:
    """Load experiment metadata from YAML file."""
    with open(metadata_path) as f:
        metadata = yaml.safe_load(f)
    return metadata


class ModuleParserFactory:
    """Factory for creating module parsers and modules from metadata."""

    _parsers: Dict[str, ModuleParserABC] = {}

    @classmethod
    def register_parser(cls, parser: ModuleParserABC):
        """Register a module parser."""
        cls._parsers[parser.get_module_type()] = parser

    @classmethod
    def create_module_from_metadata(
        cls,
        metadata_path: Path,
        module_type: Optional[str] = None,
        module_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[Any, List[Any]]:
        """
        Create module instance(s) from metadata.

        Args:
            metadata_path: Path to experiment_metadata.yml
            module_type: Optional module type override (otherwise inferred from metadata)
            metadata: Optional pre-loaded metadata dict (if provided, metadata_path is only used for experiment_dir)

        Returns:
            Module instance or list of module instances if multiple modules found
        """
        if metadata is None:
            metadata = load_metadata(metadata_path)
        experiment_dir = metadata_path.parent

        # Determine module_name (required) and module_type (optional category)
        if module_name is not None:
            mod_name = module_name
            # module_type is the category (e.g., "temperature_module"), mod_name is the actual name
            mod_type = module_type
        elif module_type is not None:
            # If only module_type provided, treat it as module_name for backward compatibility
            # In this case, we don't have a category, so pass None
            mod_name = module_type
            mod_type = None
        else:
            raise ValueError(
                "Either module_type or module_name must be provided to create_module_from_metadata"
            )

        # Check for custom parser first (for future extensibility)
        parser = cls._parsers.get(mod_name)
        
        # If no custom parser registered, use generic parser
        if parser is None:
            try:
                # Pass both module_type (category) and module_name (actual name)
                parser = GenericModuleParser(module_type=mod_type, module_name=mod_name)
            except Exception as e:
                raise ValueError(
                    f"Failed to create generic parser for module '{mod_name}': {e}"
                )

        try:
            module = parser.parse_from_metadata(metadata, experiment_dir)
            return module
        except Exception as e:
            # Provide more context about which metadata section might be problematic
            error_msg = str(e)
            context_hints = []
            
            # Check if error mentions specific fields
            if "general-input-data" in error_msg or "general_input_data" in error_msg:
                context_hints.append("Check 'general-input-data' field in metadata")
            if "module-specific-input-data" in error_msg or "module_specific_input_data" in error_msg:
                context_hints.append("Check 'module-specific-input-data' field in metadata")
            if "output-data-location" in error_msg or "output_data_location" in error_msg:
                context_hints.append("Check 'output-data-location' field in metadata")
            if f"{mod_name}" in error_msg and ("inputs" in error_msg or "input" in error_msg.lower()):
                context_hints.append(f"Check metadata.{mod_name}.inputs section")
            if f"{mod_name}" in error_msg and ("outputs" in error_msg or "output" in error_msg.lower()):
                context_hints.append(f"Check metadata.{mod_name}.outputs section")
            
            hint_text = f" Hints: {', '.join(context_hints)}" if context_hints else ""
            raise ValueError(
                f"Error parsing module '{mod_name}': {error_msg}{hint_text}"
            ) from e

    @classmethod
    def create_all_modules_from_metadata(
        cls, metadata_path: Path) -> List[Any]:
        """
        Create all modules specified in metadata.

        This method extracts module names from the metadata manifest
        (temperature_module, sealevel_modules, etc.) and creates modules for each.

        Args:
            metadata_path: Path to experiment_metadata.yml

        Returns:
            List of module instances
        """
        from facts_experiment_builder.adapters.adapter_utils import parse_manifest_from_metadata
        
        metadata = load_metadata(metadata_path)
        experiment_dir = metadata_path.parent
        
        # Parse manifest to get module names
        manifest = parse_manifest_from_metadata(metadata)
        modules = []

        # Collect all module names with their types from manifest
        modules_to_create = []
        if manifest.get("temperature_module") and manifest["temperature_module"].upper() != "NONE":
            modules_to_create.append(("temperature_module", manifest["temperature_module"]))
        for module_name in manifest.get("sealevel_modules", []):
            modules_to_create.append(("sealevel_module", module_name))
        for module_name in manifest.get("framework_modules", []):
            modules_to_create.append(("framework_module", module_name))
        for module_name in manifest.get("esl_modules", []):
            modules_to_create.append(("extreme_sealevel_module", module_name))

        for module_type, module_name in modules_to_create:
            # Check for custom parser first (for future extensibility)
            parser = cls._parsers.get(module_name)
            
            # If no custom parser, use generic parser
            if parser is None:
                try:
                    parser = GenericModuleParser(module_type=module_type, module_name=module_name)
                except Exception as e:
                    print(
                        f"Warning: Failed to create generic parser for module '{module_name}': {e}"
                    )
                    continue
            
            try:
                module = parser.parse_from_metadata(metadata, experiment_dir)
                modules.append(module)
            except Exception as e:
                print(
                    f"Warning: Failed to parse module '{module_name}': {e}"
                )
                continue

        return modules


    @classmethod
    def get_available_parsers(cls) -> List[str]:
        """Get list of available parser types."""
        return list(cls._parsers.keys())
