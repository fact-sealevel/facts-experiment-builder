#!/usr/bin/env python3
"""Generate Docker Compose file from experiment metadata.

This script follows a domain-driven design pattern:
- v2-experiment-metadata.yml is the "user interface" (UI layer)
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
    - Service level: 3 spaces
    - Properties: 6 spaces  
    - Nested properties (e.g., depends_on.fair): 9 spaces
    - Nested property values (e.g., depends_on.fair.condition): 12 spaces
    - List items: 9 spaces
    """
    lines = content.split('\n')
    formatted_lines = []
    prev_line_was_list_property = False
    in_depends_on = False
    in_depends_on_service = False
    
    for i, line in enumerate(lines):
        if not line.strip():  # Empty line
            formatted_lines.append('')
            prev_line_was_list_property = False
            in_depends_on = False
            in_depends_on_service = False
            continue
            
        stripped = line.lstrip()
        leading_spaces = len(line) - len(stripped)
        
        # Check if this is a list item (starts with '-')
        is_list_item = stripped.startswith('-')
        
        # Track depends_on nesting
        if stripped == 'depends_on:':
            in_depends_on = True
            in_depends_on_service = False
        elif in_depends_on and stripped.endswith(':') and not is_list_item and not stripped.startswith('condition') and stripped != 'depends_on:' and leading_spaces == 9:
            # This is a service name under depends_on (e.g., 'fair:')
            in_depends_on_service = True
        elif in_depends_on_service and (stripped.startswith('condition') or leading_spaces >= 12):
            # This is a property under depends_on.service (e.g., 'condition: ...')
            # Keep in_depends_on_service = True for proper indentation
            pass
        elif leading_spaces == 6 and stripped.endswith(':') and stripped not in ['depends_on:', 'fair:', 'condition:']:
            # We've left the depends_on section (new property at same level as depends_on)
            in_depends_on = False
            in_depends_on_service = False
        
        # Check if previous line was a list property (command:, volumes:, etc.)
        if i > 0 and prev_line_was_list_property and is_list_item:
            # List item under a list property - 9 spaces
            formatted_lines.append('         ' + stripped)
        elif stripped.startswith('services:'):
            # Root level - no change
            formatted_lines.append(line)
            in_depends_on = False
            in_depends_on_service = False
        elif leading_spaces == 0:
            # Root level
            formatted_lines.append(line)
            in_depends_on = False
            in_depends_on_service = False
        elif leading_spaces <= 3:
            # Service level - ensure 3 spaces
            formatted_lines.append('   ' + stripped)
            in_depends_on = False
            in_depends_on_service = False
        elif in_depends_on_service and (stripped.startswith('condition') or leading_spaces >= 12):
            # Property under depends_on.service - 12 spaces (e.g., 'condition: service_completed_successfully')
            formatted_lines.append('            ' + stripped)
        elif in_depends_on and stripped.endswith(':') and not is_list_item and stripped != 'depends_on:':
            # Service name under depends_on - 9 spaces (e.g., 'fair:')
            formatted_lines.append('         ' + stripped)
        elif is_list_item:
            # List item at property level - should be 9 spaces
            formatted_lines.append('         ' + stripped)
            prev_line_was_list_property = False
            # Check if we're leaving depends_on section
            if leading_spaces <= 6:
                in_depends_on = False
                in_depends_on_service = False
        else:
            # Property level - ensure 6 spaces
            formatted_lines.append('      ' + stripped)
            # Check if this property is a list property
            prev_line_was_list_property = stripped.endswith(':') and stripped in ['command:', 'volumes:', 'depends_on:']
            # Only reset depends_on tracking if we're not in depends_on section
            if stripped != 'depends_on:' and not in_depends_on:
                in_depends_on = False
                in_depends_on_service = False
    
    return '\n'.join(formatted_lines)

from facts_experiment_builder.adapters.module_adapter import (
    ModuleParserFactory,
    load_metadata,
)


def module_name_to_dir_name(module_name: str) -> str:
    """Convert module name (with hyphens) to directory name.
    
    Module names in metadata use hyphens (e.g., 'bamber19-icesheets'),
    and directory names also use hyphens (not underscores).
    
    Args:
        module_name: Module name from metadata (e.g., 'bamber19-icesheets')
        
    Returns:
        Directory name (e.g., 'bamber19-icesheets')
    """
    # Module names and directory names both use hyphens
    # This function exists to make the mapping explicit and allow for
    # future changes if needed
    return module_name


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
                if isinstance(inputs, dict) and "input_dir" in inputs:
                    input_dir = inputs["input_dir"]
                    if isinstance(input_dir, str):
                        # Replace underscore pattern with hyphen pattern in the path
                        normalized_path = input_dir.replace(underscore_pattern, hyphen_pattern)
                        if normalized_path != input_dir:
                            inputs = inputs.copy()
                            inputs["input_dir"] = normalized_path
                            module_section = module_section.copy()
                            module_section["inputs"] = inputs
                            normalized_metadata[module_name] = module_section
    
    return normalized_metadata


def parse_manifest_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the experiment manifest from metadata.
    
    This extracts which modules are specified in the experiment.
    
    Args:
        metadata: Loaded metadata dictionary
        
    Returns:
        Dictionary with module specifications
    """
    manifest = {
        "temp_module": metadata.get("temp_module"),
        "sealevel_modules": metadata.get("sealevel_modules", []),
        "framework_modules": metadata.get("framework_modules", []),
        "esl_modules": metadata.get("esl_modules", []),
    }
    
    # Normalize sealevel_modules to list
    if isinstance(manifest["sealevel_modules"], str):
        manifest["sealevel_modules"] = [manifest["sealevel_modules"]]
    
    return manifest


def generate_compose_from_metadata(metadata_path: Path) -> Dict[str, Any]:
    """
    Generate Docker Compose file from experiment metadata.
    
    This is the main orchestration function that:
    1. Loads metadata (UI layer)
    2. Parses manifest to determine which modules to include
    3. Uses parsers (Adapter layer) to create domain objects (modules)
    4. Generates docker compose services (Engine/Infrastructure layer)
    
    Args:
        metadata_path: Path to v2-experiment-metadata.yml
        
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
    modules = []
    
    # Create temperature module if specified
    if manifest["temp_module"]:
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type=manifest["temp_module"],
                metadata=metadata
            )
            modules.append(module)
            print(f"✓ Created {manifest['temp_module']} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create temp module '{manifest['temp_module']}': {e}")
    
    # Create sea level modules if specified
    for module_name in manifest["sealevel_modules"]:
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type=module_name,
                metadata=metadata
            )
            modules.append(module)
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create sealevel module '{module_name}': {e}")
    
    # Create framework modules if specified
    for module_name in manifest.get("framework_modules", []):
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type=module_name,
                metadata=metadata
            )
            modules.append(module)
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create framework module '{module_name}': {e}")
    
    # Create ESL modules if specified
    for module_name in manifest.get("esl_modules", []):
        try:
            module = ModuleParserFactory.create_module_from_metadata(
                metadata_path,
                module_type=module_name,
                metadata=metadata
            )
            modules.append(module)
            print(f"✓ Created {module_name} module")
        except Exception as e:
            print(f"⚠ Warning: Failed to create ESL module '{module_name}': {e}")
    
    if not modules:
        raise ValueError(
            "No modules could be created from metadata. "
            "Please ensure at least one module is specified and has valid configuration."
        )
    
    # Step 4: Generate Docker Compose services (Engine/Infrastructure layer)
    services = {}
    
    # Find fair module to get its output directory for sealevel modules
    fair_module = None
    fair_output_dir = None
    for module in modules:
        if hasattr(module, 'module_name') and module.module_name == 'fair':
            fair_module = module
            fair_output_dir = module.output_paths.fair_out_dir
            break
    
    for module in modules:
        # Use simple module name as service name (e.g., "fair", "bamber19-icesheets")
        service_name = module.module_name
        
        # Generate compose service from domain object
        # For sealevel modules, pass fair output directory if available
        if fair_module and fair_module != module:
            # Check if this is a sealevel module that needs fair output
            from facts_experiment_builder.core.modules.abcs.sealevel_module_abcs import SealevelModuleABC
            if isinstance(module, SealevelModuleABC):
                # Try calling with fair_output_dir parameter
                try:
                    compose_service = module.generate_compose_service(fair_output_dir=fair_output_dir)
                except TypeError:
                    # Fallback if method doesn't accept the parameter
                    compose_service = module.generate_compose_service()
            else:
                compose_service = module.generate_compose_service()
        else:
            compose_service = module.generate_compose_service()
        
        services[service_name] = compose_service
    
    # Step 5: Build complete Docker Compose file
    compose_file = {
        "services": services
    }
    
    return compose_file


def main():
    """Main entry point for generating Docker Compose from metadata."""
    parser = argparse.ArgumentParser(
        description="Generate Docker Compose file from experiment metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script follows a domain-driven design pattern:
- v2-experiment-metadata.yml is the "user interface" (UI layer)
- Module parsers adapt user inputs into domain terms (Adapter layer)
- Docker compose files are the "engine" (Infrastructure layer)

Example:
    python -m facts_experiment_builder.application.generate_compose v2_experiments/my_experiment
        """
    )
    parser.add_argument(
        "experiment_dir",
        type=Path,
        help="Path to experiment directory containing v2-experiment-metadata.yml"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for compose file (defaults to experiment_dir/v2-compose.yaml)"
    )
    
    args = parser.parse_args()
    
    # Handle experiment path: if it's just a name, look in v2_experiments/
    experiment_path = Path(args.experiment_dir)
    
    # First, try to resolve it as-is (in case it's a relative or absolute path)
    if experiment_path.exists():
        experiment_dir = experiment_path.resolve()
    else:
        # If it doesn't exist, check if it's just an experiment name
        # Look in v2_experiments/ subdirectory
        project_root = find_project_root()
        v2_experiments_dir = project_root / "v2_experiments"
        potential_experiment_dir = v2_experiments_dir / str(experiment_path)
        
        if potential_experiment_dir.exists():
            experiment_dir = potential_experiment_dir
        else:
            # Try resolving as a relative path from current directory
            try:
                experiment_dir = experiment_path.resolve()
            except:
                # If all else fails, assume it's an experiment name in v2_experiments/
                experiment_dir = potential_experiment_dir
    
    metadata_path = experiment_dir / "v2-experiment-metadata.yml"
    
    print(f"Generating Docker Compose from: {metadata_path}")
    print("=" * 70)
    
    try:
        # Generate compose file
        compose_file = generate_compose_from_metadata(metadata_path)
        
        # Determine output path
        if args.output is None:
            output_path = experiment_dir / "v2-compose.yaml"
        else:
            output_path = args.output.resolve()
        
        # Write to file with custom indentation
        # First dump to string
        yaml_content = yaml.dump(
            compose_file,
            default_flow_style=False,
            sort_keys=False,
            indent=3,  # 3 spaces for each level
            width=1000,  # Wide width to avoid line wrapping
            allow_unicode=True
        )
        
        # Post-process to fix indentation
        formatted_content = format_compose_yaml(yaml_content)
        
        # Write to file
        with open(output_path, "w") as f:
            f.write(formatted_content)
        
        print("=" * 70)
        print(f"✓ Generated Docker Compose file: {output_path}")
        print(f"  Services: {', '.join(compose_file['services'].keys())}")
        print(f"\nTo run the experiment:")
        print(f"  cd {experiment_dir}")
        print(f"  docker compose -f {output_path.name} up")
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

