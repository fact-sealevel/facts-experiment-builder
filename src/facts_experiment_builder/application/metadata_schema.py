"""Metadata schema generator for creating templates from domain models.

This module provides functionality to introspect module definitions (domain layer)
and generate metadata YAML templates or schemas. This respects DDD principles by:
- Domain layer: Defines what's required (dataclasses)
- Application layer: Knows how to extract (parsers) and generate schemas (this module)
- Infrastructure layer: File I/O, YAML generation (handled by callers)
"""

from dataclasses import fields, is_dataclass
from typing import Dict, Any, Type, Optional, List
from pathlib import Path
import yaml

from facts_experiment_builder.adapters.module_adapter import ModuleParserFactory
from facts_experiment_builder.adapters.abstract_adapter import ModuleParserABC


class MetadataSchemaGenerator:
    """Generates metadata schemas/templates by introspecting domain models.
    
    This service introspects module dataclasses to determine required fields
    and generates corresponding metadata YAML templates.
    """
    
    def get_dataclass_fields(self, dataclass_type: Type) -> Dict[str, Any]:
        """Extract field information from a dataclass type.
        
        Args:
            dataclass_type: The dataclass class to introspect
            
        Returns:
            Dictionary mapping field names to their type annotations and default values
        """
        if not is_dataclass(dataclass_type):
            return {}
        
        field_info = {}
        for field in fields(dataclass_type):
            field_info[field.name] = {
                'type': field.type,
                'default': field.default if field.default != field.default_factory else None,
                'required': field.default == field.default_factory and field.default_factory == type(None),
            }
            # Check if field has a default value
            if field.default != field.default_factory:
                field_info[field.name]['required'] = False
            else:
                field_info[field.name]['required'] = True
        
        return field_info
    
    def get_module_inputs_structure(self, module_type: str) -> Dict[str, Any]:
        """Get the structure of inputs required for a module.
        
        This introspects the module's Inputs dataclass to determine what fields
        are required in the metadata.
        
        Args:
            module_type: The module type (e.g., 'fair', 'bamber19-icesheets')
            
        Returns:
            Dictionary describing the required structure for this module's metadata section
        """
        # Import module-specific classes based on module type
        if module_type == "fair":
            from facts_experiment_builder.core.modules.fair.module import (
                FairInputs, FairOptions, FairInputPaths, FairOutputPaths
            )
            inputs_class = FairInputs
            options_class = FairOptions
            input_paths_class = FairInputPaths
            output_paths_class = FairOutputPaths
        elif module_type == "bamber19-icesheets":
            from facts_experiment_builder.core.modules.bamber19_icesheets.module import (
                Bamber19Inputs, Bamber19Options, 
                Bamber19IcesheetsInputPaths, Bamber19IcesheetsOutputPaths
            )
            inputs_class = Bamber19Inputs
            options_class = Bamber19Options
            input_paths_class = Bamber19IcesheetsInputPaths
            output_paths_class = Bamber19IcesheetsOutputPaths
        else:
            raise ValueError(f"Module type {module_type} not yet supported for schema generation")
        
        # Get fields from each component
        options_fields = self.get_dataclass_fields(options_class)
        input_paths_fields = self.get_dataclass_fields(input_paths_class)
        output_paths_fields = self.get_dataclass_fields(output_paths_class)
        
        # Separate top-level options from module-specific options
        # Based on parser logic: top-level fields are read from metadata root,
        # module-specific fields are read from module.inputs section
        
        # Get base class fields to identify top-level vs module-specific
        base_options_fields = set()
        if module_type == "fair":
            from facts_experiment_builder.core.modules.abcs.temp_module_abcs import TempModuleOptions
            base_options_fields = set(self.get_dataclass_fields(TempModuleOptions).keys())
            # For fair, top-level are: pipeline-id, nsamps, seed, scenario
            # Module-specific in inputs: cyear_start, cyear_end, smooth_win
            top_level_fields = {'pipeline_id', 'nsamps', 'seed', 'scenario'}
        elif module_type == "bamber19-icesheets":
            from facts_experiment_builder.core.modules.abcs.sealevel_module_abcs import SealevelModuleOptions
            base_options_fields = set(self.get_dataclass_fields(SealevelModuleOptions).keys())
            # For bamber19, top-level are: pipeline-id, nsamps, seed, scenario, pyear_start, pyear_end, pyear_step, baseyear
            # Module-specific in inputs: replace
            top_level_fields = {'pipeline_id', 'nsamps', 'seed', 'scenario', 
                              'pyear_start', 'pyear_end', 'pyear_step', 'baseyear'}
        else:
            top_level_fields = set()
        
        # Module-specific options (not top-level, not module_name/scenario which are handled specially)
        module_specific_options = {
            k: v for k, v in options_fields.items() 
            if k not in top_level_fields and k != 'module_name' and k != 'scenario'
        }
        
        # Input paths fields (excluding path_type which is set internally)
        # Map field names to metadata keys based on parser expectations
        input_paths_mapping = {}
        if module_type == "fair":
            # Parser expects: input_dir, rcmip_fname, param_fname
            input_paths_mapping = {
                'input_dir': {'type': str, 'required': True, 'description': 'Input directory path'},
                'rcmip_fname': input_paths_fields.get('rcmip_fname', {'type': str, 'required': True}),
                'param_fname': input_paths_fields.get('param_fname', {'type': str, 'required': True}),
            }
        elif module_type == "bamber19-icesheets":
            # Parser expects: input_dir, replace, slr_proj_mat_file, climate_data_file
            input_paths_mapping = {
                'input_dir': {'type': str, 'required': True, 'description': 'Input directory path'},
                'slr_proj_mat_file': input_paths_fields.get('bamber19_slr_proj_mat_file', {'type': str, 'required': True}),
                'climate_data_file': input_paths_fields.get('climate_data_file', {'type': str, 'required': True}),
            }
        
        # Output paths fields (excluding path_type)
        # For outputs, we just need the count/names, not the full structure
        output_count = len([k for k in output_paths_fields.keys() if k not in ['path_type', 'bamber19_icesheets_out_dir', 'fair_out_dir']])
        
        return {
            'inputs': {
                **input_paths_mapping,
                **module_specific_options,
            },
            'outputs_count': output_count,
            'image': {'type': str, 'required': True},
        }
    
    def generate_module_template(self, module_type: str) -> Dict[str, Any]:
        """Generate a YAML template structure for a module.
        
        Args:
            module_type: The module type (e.g., 'fair', 'bamber19-icesheets')
            
        Returns:
            Dictionary representing the YAML structure for this module
        """
        structure = self.get_module_inputs_structure(module_type)
        
        template = {
            'inputs': {}
        }
        
        # Add input fields with placeholder values
        for field_name, field_info in structure['inputs'].items():
            if field_info['type'] == int:
                template['inputs'][field_name] = 0  # Placeholder
            elif field_info['type'] == bool:
                template['inputs'][field_name] = False
            elif field_info['type'] == str:
                # Special handling for path-like fields
                if 'dir' in field_name or 'path' in field_name:
                    template['inputs'][field_name] = "$HOME/path/to/input"
                elif 'fname' in field_name or 'file' in field_name:
                    template['inputs'][field_name] = "filename.ext"
                else:
                    template['inputs'][field_name] = "value"
            else:
                template['inputs'][field_name] = None
        
        # Add image
        template['image'] = "ghcr.io/fact-sealevel/module:version"
        
        # Add outputs (list of filenames)
        output_count = structure.get('outputs_count', 3)
        if module_type == "fair":
            template['outputs'] = [
                f"{module_type}/climate.nc",
                f"{module_type}/ohc.nc",
                f"{module_type}/gsat.nc",
            ]
        elif module_type == "bamber19-icesheets":
            template['outputs'] = [
                f"{module_type}/ais_gslr.nc",
                f"{module_type}/eais_gslr.nc",
                f"{module_type}/wais_gslr.nc",
                f"{module_type}/gis_gslr.nc",
            ]
        else:
            template['outputs'] = [f"{module_type}/output_{i}.nc" for i in range(output_count)]
        
        return template
    
    def generate_experiment_template(
        self, 
        temp_module: Optional[str] = None,
        sealevel_modules: Optional[List[str]] = None,
        framework_modules: Optional[List[str]] = None,
        esl_modules: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete experiment metadata template.
        
        Args:
            temp_module: Temperature module type (e.g., 'fair')
            sealevel_modules: List of sea-level module types
            framework_modules: List of framework module types
            esl_modules: List of ESL module types
            
        Returns:
            Complete YAML structure for an experiment
        """
        template = {
            'experiment_name': "my_experiment",
            'pipeline-id': "AAAA",
            'scenario': "ssp585",
            'baseyear': 2005,
            'pyear_start': 2020,
            'pyear_end': 2150,
            'pyear_step': 10,
            'nsamps': 500,
            'seed': 1234,
            'common-inputs-path': "$HOME/path/to/common_inputs",
            'location-file': "location.lst",
            'v2-output-path': "$HOME/path/to/output",
        }
        
        if temp_module:
            template['temp_module'] = temp_module
            template[temp_module] = self.generate_module_template(temp_module)
        
        if sealevel_modules:
            template['sealevel_modules'] = sealevel_modules
            for module in sealevel_modules:
                template[module] = self.generate_module_template(module)
        
        if framework_modules:
            template['framework_modules'] = framework_modules
        
        if esl_modules:
            template['esl_modules'] = esl_modules
        
        return template
    
    def generate_template_yaml(
        self,
        output_path: Path,
        temp_module: Optional[str] = None,
        sealevel_modules: Optional[List[str]] = None,
        framework_modules: Optional[List[str]] = None,
        esl_modules: Optional[List[str]] = None,
    ) -> None:
        """Generate a YAML template file.
        
        Args:
            output_path: Path where the template YAML file should be written
            temp_module: Temperature module type
            sealevel_modules: List of sea-level module types
            framework_modules: List of framework module types
            esl_modules: List of ESL module types
        """
        template = self.generate_experiment_template(
            temp_module=temp_module,
            sealevel_modules=sealevel_modules,
            framework_modules=framework_modules,
            esl_modules=esl_modules,
        )
        
        with open(output_path, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        
        print(f"Generated metadata template at: {output_path}")

