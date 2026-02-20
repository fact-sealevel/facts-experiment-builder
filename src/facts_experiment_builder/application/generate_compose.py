#!/usr/bin/env python3
"""Generate Docker Compose file from experiment metadata.

This script follows a domain-driven design pattern:
- experiment-metadata.yml is the "user interface" (UI layer)
- Module service specs are created from experiment metadata (Adapter layer)
- Docker compose files are the "engine" (Infrastructure layer)

Usage:
    python -m facts_experiment_builder.application.generate_compose <experiment_dir>
    
"""


import yaml
from pathlib import Path
from typing import Dict, Any, List

from facts_experiment_builder.adapters.module_adapter import (
    create_module_service_spec_from_metadata,
)

from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.infra.path_manager import find_module_yaml_path
from facts_experiment_builder.infra.path_utils import find_project_root
from facts_experiment_builder.infra.experiment_loader import load_experiment_metadata



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
        project_root = find_project_root(experiment_dir)
        module_yaml_path = find_module_yaml_path(module_name, project_root)
        with open(module_yaml_path, 'r') as f:
            module_config = yaml.safe_load(f) or {}
        return module_config.get("climate_file_required", True)
    except (FileNotFoundError, Exception):
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
        raise FileNotFoundError(f"When trying to read experiment-metadata file to generate corresponding compose file, metadata file not found: {metadata_path}")
    
    # Step 1: Load metadata (UI layer)
    metadata = load_experiment_metadata(metadata_path)

    experiment_dir = metadata_path.parent

    # Step 2: Build FactsExperiment and get manifest
    experiment = FactsExperiment.from_metadata_dict(metadata)
    manifest = experiment.manifest

    # Step 3: Create ModuleServiceSpec instances using parsers (Adapter layer -> Domain layer)
    #modules = []
    modules = {
        'temperature_module': None,
        'sealevel_modules': {},
        'framework_modules': {},
        'esl_modules': {},
    }
    
    # Create temperature module if specified (and not "NONE")
    temperature_module_name = manifest["temperature_module"]
    if temperature_module_name and temperature_module_name.upper() != "NONE":
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=temperature_module_name,
                module_type="temperature_module",
                metadata=metadata,
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
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=module_name,
                module_type="sealevel_module",
                metadata=metadata,
            )
            #modules.append(module)
            modules['sealevel_modules'][module_name] = module
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create sealevel module '{module_name}': {e}")
    
    # Create framework modules if specified
    for module_name in manifest.get("framework_modules", []):
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=module_name,
                module_type="framework_module",
                metadata=metadata,
            )
            modules['framework_modules'][module_name] = module
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create framework module '{module_name}': {e}")
    
    # Create ESL modules if specified
    for module_name in manifest.get("esl_modules", []):
        try:
            module = create_module_service_spec_from_metadata(
                metadata_path,
                module_name=module_name,
                module_type="extreme_sealevel_module",
                metadata=metadata,
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
    
    # Step 5: Build complete Docker Compose file as dict
    compose_dict = {
        "services": services
    }
    
    return compose_dict