"""Factory and utilities for creating modules from experiment metadata."""

import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from facts_experiment_builder.adapters.abstract_adapter import (
    ModuleParserABC,
)
from facts_experiment_builder.core.modules.fair.parser import FairModuleParser
from facts_experiment_builder.core.modules.bamber19_icesheets.parser import (
    Bamber19ModuleParser,
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

        # Determine module type(s)
        if module_type is None:
            module_types = cls._infer_module_types(metadata)
        else:
            module_types = [module_type]

        # Get parsers and create modules
        modules = []
        for mod_type in module_types:
            parser = cls._parsers.get(mod_type)
            if parser is None:
                raise ValueError(
                    f"No parser registered for module type: {mod_type}. "
                    f"Available parsers: {list(cls._parsers.keys())}"
                )

            try:
                module = parser.parse_from_metadata(metadata, experiment_dir)
                modules.append(module)
            except Exception as e:
                raise ValueError(
                    f"Error parsing module type '{mod_type}': {e}"
                ) from e

        # Return single module if only one, otherwise return list
        return modules[0] if len(modules) == 1 else modules

    @classmethod
    def create_all_modules_from_metadata(
        cls, metadata_path: Path
    ) -> List[Any]:
        """
        Create all modules specified in metadata.

        Args:
            metadata_path: Path to experiment_metadata.yml

        Returns:
            List of module instances
        """
        metadata = load_metadata(metadata_path)
        experiment_dir = metadata_path.parent

        module_types = cls._infer_module_types(metadata)
        modules = []

        for module_type in module_types:
            parser = cls._parsers.get(module_type)
            if parser:
                try:
                    module = parser.parse_from_metadata(metadata, experiment_dir)
                    modules.append(module)
                except Exception as e:
                    print(
                        f"Warning: Failed to parse module type '{module_type}': {e}"
                    )
                    continue

        return modules

    @classmethod
    def _infer_module_types(cls, metadata: Dict[str, Any]) -> List[str]:
        """
        Infer module types from metadata.

        Checks v2-output-files keys to determine which modules are present.
        """
        output_files = metadata.get(
            "v2-output-files", metadata.get("v2_output_files", {})
        )

        module_types = []
        for key in output_files.keys():
            if key == "fair":
                if "fair" not in module_types:
                    module_types.append("fair")
            elif "bamber19" in key.lower():
                if "bamber19-icesheets" not in module_types:
                    module_types.append("bamber19-icesheets")
            # Add more module type detection logic here as needed
            # elif "ar5" in key.lower():
            #     if "ar5-icesheets" not in module_types:
            #         module_types.append("ar5-icesheets")

        if not module_types:
            raise ValueError(
                "Could not infer module type(s) from metadata. "
                "No recognized module output files found in v2-output-files."
            )

        return module_types

    @classmethod
    def get_available_parsers(cls) -> List[str]:
        """Get list of available parser types."""
        return list(cls._parsers.keys())


# Register parsers on module import
ModuleParserFactory.register_parser(FairModuleParser())
ModuleParserFactory.register_parser(Bamber19ModuleParser())
