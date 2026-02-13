#!/usr/bin/env python3
"""Generate Docker Compose file from experiment metadata.

This script follows a domain-driven design pattern:
- experiment-metadata.yml is the "user interface" (UI layer)
- Module parsers adapt user inputs into domain terms (Adapter layer)
- Docker compose files are the "engine" (Infrastructure layer)

Usage:
    python -m facts_experiment_builder.application.generate_compose <experiment_dir>
    
Example:
    python -m facts_experiment_builder.application.generate_compose v2_experiments/my_experiment
"""

import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List


def find_project_root(start_path: Path = None) -> Path:
    """
    Find the project root by looking for pyproject.toml.
    
    Args:
        start_path: Path to start searching from (defaults to current working directory)
        
    Returns:
        Path to project root (directory containing pyproject.toml)
        
    Raises:
        FileNotFoundError: If pyproject.toml is not found
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()
    
    # Walk up the directory tree looking for pyproject.toml
    current = start_path
    while current != current.parent:  # Stop at filesystem root
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return current
        current = current.parent
    
    raise FileNotFoundError(
        f"Could not find pyproject.toml. Searched from {start_path}"
    )


def format_compose_yaml(content: str) -> str:
    """Post-process YAML content to match desired indentation style.
    
    Converts:
    - Root level (services:): 0 spaces
    - Step level (temperature module, sealevel modules): 3 spaces
    - Service level (bamber19-icesheets:, deconto21-ais:): 6 spaces
    - Service properties (image:, command:, volumes:): 9 spaces
    - List items (command args, volumes): 12 spaces
    - Nested properties (depends_on.fair): 12 spaces
    - Nested property values (depends_on.fair.condition): 15 spaces
    - Command arguments: Adds double quotes around values
    """
    lines = content.split('\n')
    formatted_lines = []
    prev_line_was_list_property = False
    in_depends_on = False
    in_depends_on_service = False
    in_command = False  # Track if we're in a command section
    in_service = False  # Track if we're inside a service (under a service name)
    prev_line_was_service_name = False  # Track if previous line was a service name
    prev_line_was_depends_on_service = False  # Track if previous line was a service name under depends_on
    
    for i, line in enumerate(lines):
        if not line.strip():  # Empty line
            formatted_lines.append('')
            prev_line_was_list_property = False
            in_depends_on = False
            in_depends_on_service = False
            in_command = False
            prev_line_was_service_name = False
            prev_line_was_depends_on_service = False
            continue
            
        stripped = line.lstrip()
        leading_spaces = len(line) - len(stripped)
        
        # Check if this is a list item (starts with '-')
        is_list_item = stripped.startswith('-')
        
        # Detect service names (lines ending with ':' that are at 6 spaces, not list items, and not known properties)
        is_service_name = (leading_spaces == 6 and 
                          stripped.endswith(':') and 
                          not is_list_item and
                          stripped not in ['image:', 'command:', 'volumes:', 'depends_on:', 'restart:', 'condition:'])
        
        # Track command section
        if stripped == 'command:':
            in_command = True
        elif leading_spaces <= 9 and stripped.endswith(':') and stripped != 'command:' and not is_list_item:
            # We've left the command section (new property at same or higher level)
            in_command = False
        
        # Track depends_on nesting
        if stripped == 'depends_on:':
            in_depends_on = True
            in_depends_on_service = False
        elif in_depends_on and stripped.endswith(':') and not is_list_item and not stripped.startswith('condition') and stripped != 'depends_on:':
            # This could be a service name under depends_on (e.g., 'fair:')
            # Check if it's at the right indentation level (should be 9-12 spaces when in_service)
            if in_service and (leading_spaces >= 9 and leading_spaces <= 12):
                in_depends_on_service = True
            elif not in_service and leading_spaces == 12:
                in_depends_on_service = True
        elif in_depends_on_service and stripped.startswith('condition'):
            # This is a property under depends_on.service (e.g., 'condition: ...')
            # Keep in_depends_on_service = True for proper indentation
            pass
        elif in_service and leading_spaces == 9 and stripped.endswith(':') and stripped not in ['depends_on:', 'fair:', 'condition:', 'command:', 'volumes:', 'restart:']:
            # We've left the depends_on section (new property at same level as depends_on)
            in_depends_on = False
            in_depends_on_service = False
        elif not in_service and leading_spaces <= 6 and stripped.endswith(':') and stripped not in ['depends_on:', 'fair:', 'condition:']:
            # We've left the depends_on section (new property at same or higher level)
            in_depends_on = False
            in_depends_on_service = False
        
        # Track if we're inside a service
        if is_service_name:
            in_service = True
            prev_line_was_service_name = True
        elif leading_spaces <= 6 and stripped.endswith(':') and not is_list_item:
            # We've left the service (new step-level key)
            in_service = False
            prev_line_was_service_name = False
        
        # Check if previous line was a list property (command:, volumes:, etc.)
        if i > 0 and prev_line_was_list_property and is_list_item:
            # List item under a list property
            # If we're in a service, use 12 spaces; otherwise 9 spaces
            indent = '            ' if in_service else '         '
            formatted_item = indent + stripped
            # If this is a command argument, add double quotes around the value
            if in_command and stripped.startswith('-'):
                # Extract everything after the dash and space
                if len(stripped) > 2 and stripped[1] == ' ':
                    value = stripped[2:]  # Everything after '- '
                    # Check if value is already quoted
                    if not (value.startswith('"') and value.endswith('"')):
                        # Add quotes around the value
                        formatted_item = indent + '- "' + value + '"'
                    else:
                        formatted_item = indent + stripped
                else:
                    formatted_item = indent + stripped
            formatted_lines.append(formatted_item)
        elif stripped.startswith('services:') or stripped.startswith('steps:'):
            # Root level - no change
            formatted_lines.append(line)
            in_depends_on = False
            in_depends_on_service = False
            in_command = False
            in_service = False
            prev_line_was_service_name = False
            prev_line_was_depends_on_service = False
        elif leading_spaces == 0:
            # Root level
            formatted_lines.append(line)
            in_depends_on = False
            in_depends_on_service = False
            in_command = False
            in_service = False
            prev_line_was_service_name = False
            prev_line_was_depends_on_service = False
        elif leading_spaces <= 3:
            # Step level (temperature module, sealevel modules) - ensure 3 spaces
            formatted_lines.append('   ' + stripped)
            in_depends_on = False
            in_depends_on_service = False
            in_command = False
            in_service = False
            prev_line_was_service_name = False
            prev_line_was_depends_on_service = False
        elif is_service_name:
            # Service name level (bamber19-icesheets:, deconto21-ais:) - ensure 6 spaces
            formatted_lines.append('      ' + stripped)
            in_depends_on = False
            in_depends_on_service = False
            in_command = False
            prev_line_was_service_name = True
        elif prev_line_was_depends_on_service and stripped.startswith('condition'):
            # Condition property immediately after a service name under depends_on - should be nested under that service
            # Use 12 spaces when in_service (nested under fair: which is at 9 spaces)
            if in_service:
                formatted_lines.append('            ' + stripped)
            else:
                formatted_lines.append('               ' + stripped)
            prev_line_was_depends_on_service = False
            in_depends_on_service = True  # Keep tracking for potential future properties
        elif in_depends_on_service and stripped.startswith('condition'):
            # Property under depends_on.service - 12 spaces (e.g., 'condition: service_completed_successfully')
            # This should be nested under the service name (fair:)
            formatted_lines.append('            ' + stripped)
        elif in_depends_on and stripped.endswith(':') and not is_list_item and stripped != 'depends_on:':
            # Service name under depends_on - 9 spaces when in_service, 12 spaces otherwise (e.g., 'fair:')
            if in_service:
                formatted_lines.append('         ' + stripped)
                prev_line_was_depends_on_service = True
            else:
                formatted_lines.append('            ' + stripped)
                prev_line_was_depends_on_service = True
        elif is_list_item:
            # List item - indent based on context
            if in_service:
                # List item inside a service - 12 spaces
                indent = '            '
            else:
                # List item at step level - 9 spaces
                indent = '         '
            formatted_item = indent + stripped
            # If this is a command argument, add double quotes around the value
            if in_command and stripped.startswith('-'):
                # Extract everything after the dash and space
                if len(stripped) > 2 and stripped[1] == ' ':
                    value = stripped[2:]  # Everything after '- '
                    # Check if value is already quoted
                    if not (value.startswith('"') and value.endswith('"')):
                        # Add quotes around the value
                        formatted_item = indent + '- "' + value + '"'
                    else:
                        formatted_item = indent + stripped
                else:
                    formatted_item = indent + stripped
            formatted_lines.append(formatted_item)
            prev_line_was_list_property = False
            # Check if we're leaving depends_on section
            if leading_spaces <= 9:
                in_depends_on = False
                in_depends_on_service = False
        else:
            # Property level
            if in_service:
                # Property inside a service (image:, command:, volumes:, etc.) - 9 spaces
                formatted_lines.append('         ' + stripped)
            else:
                # Property at step level - 6 spaces
                formatted_lines.append('      ' + stripped)
            # Check if this property is a list property
            prev_line_was_list_property = stripped.endswith(':') and stripped in ['command:', 'volumes:', 'depends_on:']
            # Only reset depends_on tracking if we're not in depends_on section
            if stripped != 'depends_on:' and not in_depends_on:
                in_depends_on = False
                in_depends_on_service = False
            prev_line_was_service_name = False
            # Reset depends_on service tracking if we've moved to a different property
            if stripped.endswith(':') and stripped not in ['depends_on:', 'fair:', 'condition:'] and leading_spaces == 9:
                prev_line_was_depends_on_service = False
    
    return '\n'.join(formatted_lines)

from facts_experiment_builder.adapters.module_adapter import (
    ModuleParserFactory,
    load_metadata,
)
from facts_experiment_builder.adapters.adapter_utils import (
    parse_manifest_from_metadata,
)




def normalize_module_paths_in_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize module input directory paths in metadata.
    
    Converts underscores to hyphens in module directory names within paths.
    For example: 'bamber19_icesheets' -> 'bamber19-icesheets' in paths.
    
    Args:
        metadata: Metadata dictionary
        
    Returns:
        Metadata dictionary with normalized paths
    """
    # Mapping of module names to their directory name patterns
    # Key: module name in metadata (with hyphens)
    # Value: tuple of (underscore_pattern, hyphen_pattern)
    module_dir_mappings = {
        "bamber19-icesheets": ("bamber19_icesheets", "bamber19-icesheets"),
        "ipccar5": ("ipccar5", "ipccar5"),  # No change needed
        "fair": ("fair", "fair"),  # No change needed
    }
    
    # Create a copy to avoid modifying the original
    normalized_metadata = metadata.copy()
    
    # Process each module section
    for module_name, (underscore_pattern, hyphen_pattern) in module_dir_mappings.items():
        if module_name in normalized_metadata:
            module_section = normalized_metadata[module_name]
            if isinstance(module_section, dict) and "inputs" in module_section:
                inputs = module_section["inputs"]
                #if isinstance(inputs, dict) and "input_dir" in inputs:
                    #input_dir = inputs["input_dir"]
                    #if isinstance(input_dir, str):
                    #    # Replace underscore pattern with hyphen pattern in the path
                    #    normalized_path = input_dir.replace(underscore_pattern, hyphen_pattern)
                    #    if normalized_path != input_dir:
                    #        inputs = inputs.copy()
                    #        inputs["input_dir"] = normalized_path
                    #        module_section = module_section.copy()
                    #        module_section["inputs"] = inputs
                    #        normalized_metadata[module_name] = module_section
    
    return normalized_metadata




def _module_requires_climate_file(module_name: str, experiment_dir: Path) -> bool:
    """
    Check if a module requires a climate file by loading its module YAML configuration.
    
    Args:
        module_name: Name of the module (e.g., 'bamber19-icesheets')
        experiment_dir: Path to experiment directory (used to find project root)
        
    Returns:
        True if climate_file_required is True in module YAML, False otherwise
    """
    try:
        # Find project root
        project_root = find_project_root(experiment_dir)
        modules_dir = project_root / "src" / "facts_experiment_builder" / "core" / "modules"
        
        # Convert module name to filename format
        # e.g., "bamber19-icesheets" -> "bamber19_icesheets_module.yaml"
        module_dir_name = module_name.replace('-', '_')
        
        possible_paths = [
            modules_dir / f"{module_dir_name}_module.yaml",
            modules_dir / f"{module_name}_module.yaml",
        ]
        
        # Special cases for naming conventions (only for specific modules)
        if module_name == "fair" or module_name.startswith("fair"):
            possible_paths.extend([
                modules_dir / "fair_temperature_module.yaml",  # Fair uses temperature in name
                modules_dir / "fair_module.yaml",  # Fallback for fair
            ])
        
        module_yaml_path = None
        for path in possible_paths:
            if path.exists():
                module_yaml_path = path
                break
        
        if module_yaml_path is None:
            # If module YAML not found, default to True for backward compatibility
            return True
        
        # Load module YAML configuration
        with open(module_yaml_path, 'r') as f:
            module_config = yaml.safe_load(f) or {}
        
        # Check climate_file_required flag (defaults to True if not specified)
        return module_config.get("climate_file_required", True)
        
    except Exception:
        # If there's any error loading the module config, default to True for safety
        return True


def _validate_climate_file_inputs(metadata: Dict[str, Any], sealevel_modules: List[str], experiment_dir: Path) -> None:
    """
    Validate that sealevel modules have climate file inputs when no temperature module is specified.
    Only validates modules that have climate_file_required=True in their module YAML.
    
    Args:
        metadata: Experiment metadata dictionary
        sealevel_modules: List of sealevel module names
        experiment_dir: Path to experiment directory (used to find module YAML files)
        
    Raises:
        ValueError: If any sealevel module that requires climate files is missing climate file input
    """
    missing_climate_files = []
    
    for module_name in sealevel_modules:
        # Check if this module requires a climate file
        if not _module_requires_climate_file(module_name, experiment_dir):
            continue
        
        module_metadata = metadata.get(module_name, {})
        module_inputs = module_metadata.get("inputs", {})
        
        # Check for various possible field names for climate file
        # Common variations: climate_data_file, climate-data-file, climate_file, climate-file, climate_data, climate-data
        climate_file = (
            module_inputs.get("climate_data_file") or 
            module_inputs.get("climate-data-file") or
            module_inputs.get("climate_file") or
            module_inputs.get("climate-file") or
            module_inputs.get("climate_data") or
            module_inputs.get("climate-data")
        )
        
        if not climate_file or (isinstance(climate_file, str) and climate_file.strip() == ""):
            missing_climate_files.append(module_name)
    
    if missing_climate_files:
        raise ValueError(
            f"No temperature module specified, but the following sealevel modules are missing "
            f"climate file inputs: {', '.join(missing_climate_files)}. "
            f"Please provide 'climate_data_file' (or 'climate-data-file', 'climate_file', etc.) "
            f"in the inputs section for each sealevel module."
        )


def generate_compose_from_metadata(metadata_path: Path) -> Dict[str, Any]:
    """
    Generate Docker Compose file from experiment metadata.
    
    This is the main orchestration function that:
    1. Loads metadata (UI layer)
    2. Parses manifest to determine which modules to include
    3. Uses parsers (Adapter layer) to create domain objects (modules)
    4. Generates docker compose services (Engine/Infrastructure layer)
    
    Args:
        metadata_path: Path to experiment-metadata.yml
        
    Returns:
        Complete Docker Compose file dictionary
    """
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    # Step 1: Load metadata (UI layer)
    metadata = load_metadata(metadata_path)
    
    # Normalize module paths (convert underscores to hyphens in directory names)
    metadata = normalize_module_paths_in_metadata(metadata)
    
    experiment_dir = metadata_path.parent
    
    # Step 2: Parse manifest
    manifest = parse_manifest_from_metadata(metadata)
    
    # Step 3: Create modules using parsers (Adapter layer -> Domain layer)
    #modules = []
    modules = {
        'temperature_module': None,
        'sealevel_modules': {},
        'framework_modules': {},
        'esl_modules': {},
    }
    
    # Create temperature module if specified (and not "NONE")
    temperature_module_name = manifest["temperature_module"]
    #print('gen_compose, line 401: manifest temp module: ', manifest['temperature_module'])
    if temperature_module_name and temperature_module_name.upper() != "NONE":
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type="temperature_module",
                module_name=temperature_module_name,
                metadata=metadata
            )
            #modules.append(module)
            modules['temperature_module'] = module
            print(f"✓ Created {temperature_module_name} module")
        except Exception as e: ### TODO What type of error to use for these?
            print(f"⚠ Warning: Failed to create temp module '{temperature_module_name}': {e}")
    elif temperature_module_name and temperature_module_name.upper() == "NONE":
        # No temperature module - validate that sealevel modules have climate file inputs
        # Only validate modules that have climate_file_required=True
        print("ℹ No temperature module specified (NONE)")
        _validate_climate_file_inputs(metadata, manifest["sealevel_modules"], experiment_dir)
    
    # Create sea level modules if specified
    for module_name in manifest["sealevel_modules"]:
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type="sealevel_module",
                module_name=module_name,
                metadata=metadata
            )
            #modules.append(module)
            modules['sealevel_modules'][module_name] = module
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create sealevel module '{module_name}': {e}")
    
    # Create framework modules if specified
    for module_name in manifest.get("framework_modules", []):
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type="framework_module",
                module_name=module_name,
                metadata=metadata
            )
            #modules.append(module)
            modules['framework_modules'][module_name] = module
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create framework module '{module_name}': {e}")
    
    # Create ESL modules if specified
    for module_name in manifest.get("esl_modules", []):
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type="extreme_sealevel_module",
                module_name=module_name,
                metadata=metadata
            )
            #modules.append(module)
            modules['esl_modules'][module_name] = module
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create ESL module '{module_name}': {e}")
    
    if (not modules['temperature_module'] and 
        not modules['sealevel_modules'] and 
        not modules['framework_modules'] and 
        not modules['esl_modules']):
        raise ValueError(
            "No modules could be created from metadata. "
            "Please ensure at least one module is specified and has valid configuration."
        )
    
    # Step 4: Generate Docker Compose services (Engine/Infrastructure layer)
    services = {}

    # Add temperature module service if present
    temperature_module = modules['temperature_module']
    temperature_module_name = temperature_module.module_name if temperature_module else None
    if temperature_module:
        services[temperature_module_name] = temperature_module.generate_compose_service()

    # Add sealevel modules directly to services (flat structure for Docker Compose)
    for module_name, module in modules['sealevel_modules'].items():
        service_name = module.module_name
        compose_service = module.generate_compose_service(
            temperature_service_name=temperature_module_name
        )
        services[service_name] = compose_service
    
    # Step 5: Build complete Docker Compose file
    compose_file = {
        "services": services
    }
    
    return compose_file