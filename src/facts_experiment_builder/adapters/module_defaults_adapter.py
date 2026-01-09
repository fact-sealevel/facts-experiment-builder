"""Adapter for extracting default values from module dataclasses."""

import dataclasses
from dataclasses import fields, is_dataclass
from typing import Dict, Any, Type, Optional
from facts_experiment_builder.core.modules.fair.module import (
    FairOptions,
    FairInputPaths,
    FairInputs,
)
from facts_experiment_builder.core.modules.bamber19_icesheets.module import (
    Bamber19Options,
    Bamber19IcesheetsInputPaths,
    Bamber19Inputs,
)


class ModuleDefaultsAdapter:
    """Adapter to extract default values from module dataclasses.
    
    Extracts defaults from:
    - Options classes (e.g., FairOptions, Bamber19Options)
    - InputPaths classes (e.g., FairInputPaths, Bamber19IcesheetsInputPaths)
    - Inputs classes (e.g., FairInputs, Bamber19Inputs)
    
    Note: The dataclass defaults are loaded from YAML files by the module.py files
    at import time, so this adapter simply introspects the dataclasses.
    """
    
    # Map module names to their dataclass types
    _module_dataclasses: Dict[str, Dict[str, Type]] = {
        "fair": {
            "options": FairOptions,
            "input_paths": FairInputPaths,
            "inputs": FairInputs,
        },
        "bamber19-icesheets": {
            "options": Bamber19Options,
            "input_paths": Bamber19IcesheetsInputPaths,
            "inputs": Bamber19Inputs,
        },
    }
    
    @classmethod
    def get_module_options_class(cls, module_name: str) -> Optional[Type]:
        """Get the Options class for a given module name.
        
        Args:
            module_name: Name of the module (e.g., 'fair', 'bamber19-icesheets')
            
        Returns:
            Options class or None if not found
        """
        module_classes = cls._module_dataclasses.get(module_name)
        if module_classes:
            return module_classes.get("options")
        return None
    
    @classmethod
    def extract_defaults_from_dataclass(cls, options_class: Type) -> Dict[str, Any]:
        """Extract default values from a dataclass.
        
        Args:
            options_class: The dataclass type to extract defaults from
            
        Returns:
            Dictionary mapping field names to their default values
        """
        if not is_dataclass(options_class):
            return {}
        
        defaults = {}
        for field in fields(options_class):
            # Check if field has a default value
            if field.default is not dataclasses.MISSING:
                defaults[field.name] = field.default
            # Check if field has a default_factory
            elif field.default_factory is not dataclasses.MISSING:
                # For default_factory, we'd need to call it, but for template
                # generation, we might want to skip these or handle specially
                defaults[field.name] = None  # or field.default_factory()
        
        return defaults
    
    @classmethod
    def get_module_defaults(cls, module_name: str) -> Dict[str, Any]:
        """Get default values for a module's options.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary of field_name -> default_value
        """
        options_class = cls.get_module_options_class(module_name)
        if options_class is None:
            return {}
        
        return cls.extract_defaults_from_dataclass(options_class)
    
    @classmethod
    def get_module_input_defaults(cls, module_name: str) -> Dict[str, Any]:
        """Get default values for module-specific inputs (not inherited from base).
        
        This extracts only the fields that are specific to the module's Options class,
        not those inherited from base classes.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary of module-specific input defaults
        """
        options_class = cls.get_module_options_class(module_name)
        if options_class is None:
            return {}
        
        # Get all fields including inherited ones
        all_fields = {f.name: f for f in fields(options_class)}
        
        # Get base class fields (if any)
        base_classes = options_class.__bases__
        base_fields = set()
        for base in base_classes:
            if is_dataclass(base):
                base_fields.update(f.name for f in fields(base))
        
        # Return only fields not in base classes
        module_specific_defaults = {}
        for field in fields(options_class):
            if field.name not in base_fields:
                if field.default is not dataclasses.MISSING:
                    module_specific_defaults[field.name] = field.default
                elif field.default_factory is not dataclasses.MISSING:
                    module_specific_defaults[field.name] = None
        
        return module_specific_defaults
    
    @classmethod
    def get_all_module_defaults(cls, module_name: str) -> Dict[str, Any]:
        """Get ALL default values for a module from dataclasses.
        
        Extracts defaults from:
        - Options class (module-specific options)
        - InputPaths class (input path defaults)
        - Inputs class (e.g., image default)
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary mapping field names to their default values
        """
        module_classes = cls._module_dataclasses.get(module_name)
        if not module_classes:
            return {}
        
        all_defaults = {}
        
        # Extract from Options class (module-specific options only)
        options_class = module_classes.get("options")
        if options_class:
            options_defaults = cls.get_module_input_defaults(module_name)
            all_defaults.update(options_defaults)
        
        # Extract from InputPaths class
        input_paths_class = module_classes.get("input_paths")
        if input_paths_class:
            input_paths_defaults = cls.extract_defaults_from_dataclass(input_paths_class)
            all_defaults.update(input_paths_defaults)
        
        # Extract from Inputs class
        inputs_class = module_classes.get("inputs")
        if inputs_class:
            inputs_defaults = cls.extract_defaults_from_dataclass(inputs_class)
            all_defaults.update(inputs_defaults)
        
        return all_defaults
    
    @classmethod
    def get_module_defaults_for_metadata(cls, module_name: str) -> Dict[str, Dict[str, Any]]:
        """Get defaults organized by metadata section (inputs, options, image).
        
        Returns a dictionary with keys:
        - 'inputs': defaults for the inputs section (includes all input fields, None if no default)
        - 'options': defaults for the options section  
        - 'image': default image value
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary with 'inputs', 'options', and 'image' keys
        """
        all_defaults = cls.get_all_module_defaults(module_name)
        module_classes = cls._module_dataclasses.get(module_name, {})
        
        result = {
            "inputs": {},
            "options": {},
            "image": None,
        }
        
        # Map field names to metadata keys
        # This mapping handles differences between dataclass field names and metadata keys
        field_to_metadata_map = {
            "fair": {
                "fair_in_dir": "input_dir",
                "cyear_start": "cyear_start",
                "cyear_end": "cyear_end",
                "smooth_win": "smooth_win",
                "rcmip_fname": "rcmip_fname",
                "param_fname": "param_fname",
            },
            "bamber19-icesheets": {
                "bamber19_icesheets_in_dir": "input_dir",
                "bamber19_slr_proj_mat_file": "slr_proj_mat_file",
                "climate_data_file": "climate_data_file",
                "replace": "replace",
            },
        }
        
        mapping = field_to_metadata_map.get(module_name, {})
        
        # Get all fields from InputPaths (even without defaults) to ensure they're included
        input_paths_class = module_classes.get("input_paths")
        if input_paths_class and is_dataclass(input_paths_class):
            for field in fields(input_paths_class):
                field_name = field.name
                metadata_key = mapping.get(field_name, field_name)
                # Use default if available, otherwise None (will be handled by setup script)
                value = all_defaults.get(field_name)
                result["inputs"][metadata_key] = value
        
        # Get all fields from Options (module-specific only)
        options_class = module_classes.get("options")
        if options_class and is_dataclass(options_class):
            # Get base class fields to exclude inherited ones
            base_classes = options_class.__bases__
            base_fields = set()
            for base in base_classes:
                if is_dataclass(base):
                    base_fields.update(f.name for f in fields(base))
            
            for field in fields(options_class):
                if field.name not in base_fields:
                    field_name = field.name
                    metadata_key = mapping.get(field_name, field_name)
                    value = all_defaults.get(field_name)
                    
                    if field_name in ["replace"]:  # Options that go in both options and inputs
                        result["options"][metadata_key] = value
                        result["inputs"][metadata_key] = value
                    elif field_name in ["cyear_start", "cyear_end", "smooth_win"]:  # FairOptions fields that go in inputs
                        result["inputs"][metadata_key] = value
        
        # Get image from Inputs class or ContainerImage class
        # Image is typically in the ContainerImage class, not Inputs
        # We need to check the module's container image class
        if module_name == "fair":
            from facts_experiment_builder.core.modules.fair.module import FairContainerImage
            image_defaults = cls.extract_defaults_from_dataclass(FairContainerImage)
            result["image"] = image_defaults.get("image_url")
        elif module_name == "bamber19-icesheets":
            from facts_experiment_builder.core.modules.bamber19_icesheets.module import Bamber19IcesheetsContainerImage
            image_defaults = cls.extract_defaults_from_dataclass(Bamber19IcesheetsContainerImage)
            result["image"] = image_defaults.get("image_url")
        
        return result

