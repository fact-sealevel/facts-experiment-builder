#!/usr/bin/env python3
"""Python script to create a new experiment directory with template files.

Usage:
    python setup_new_experiment.py <experiment_name> <temp_module> <sealevel_module> [<sealevel_module2> ...]
    
Example:
    python setup_new_experiment.py my_new_experiment fair bamber19-icesheets
    python setup_new_experiment.py my_new_experiment fair bamber19-icesheets ipccar5
"""

import sys
import shutil
import yaml
import os
from pathlib import Path
from typing import List

from facts_experiment_builder.adapters.module_defaults_adapter import ModuleDefaultsAdapter


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
    
    # If not found, try starting from __file__ location as fallback
    script_path = Path(__file__).resolve().parent
    current = script_path
    while current != current.parent:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return current
        current = current.parent
    
    raise FileNotFoundError(
        f"Could not find pyproject.toml. Searched from {start_path} and {script_path}"
    )


def write_metadata_yaml(metadata: dict, output_path: Path):
    """
    Write metadata to YAML file with custom formatting for top-level keys.
    
    Top-level keys (lines 1-14) are formatted with line breaks and indentation.
    Nested structures (modules) are written with comment handling.
    
    Args:
        metadata: Metadata dictionary
        output_path: Path to output YAML file
    """
    # Top-level keys to format specially (in order)
    top_level_keys = [
        "experiment_name",
        "pipeline-id",
        "scenario",
        "baseyear",
        "pyear_start",
        "pyear_end",
        "pyear_step",
        "nsamps",
        "seed",
        "temp_module",
        "sealevel_modules",
        "common-inputs-path",
        "location-file",
        "v2-output-path",
    ]
    
    # Write top-level keys with custom formatting
    lines = []
    for key in top_level_keys:
        if key not in metadata:
            continue
        
        value = metadata[key]
        
        # Format key with line break and indentation
        lines.append(f"{key}:")
        
        # Format value with indentation (4 spaces)
        if isinstance(value, str):
            # Quote strings that contain special characters or start with $
            if value.startswith("$") or " " in value or "/" in value:
                lines.append(f'    "{value}"')
            else:
                lines.append(f"    {value}")
        elif isinstance(value, list):
            # For lists, use yaml.dump for proper formatting
            list_yaml = yaml.dump({key: value}, default_flow_style=False, sort_keys=False)
            # Extract just the value part and indent it
            list_lines = list_yaml.split('\n')[1:]  # Skip the key line
            for line in list_lines:
                if line.strip():
                    lines.append(f"    {line}")
        else:
            lines.append(f"    {value}")
        
        lines.append("")  # Empty line between keys
    
    # Write nested module structures with comment handling
    module_keys = [k for k in metadata.keys() if k not in top_level_keys]
    if module_keys:
        lines.append("")  # Empty line before modules
        
        # Process each module separately to handle comments
        for module_key in module_keys:
            module_data = metadata[module_key]
            # Use yaml.dump to generate the module YAML
            module_yaml = yaml.dump({module_key: module_data}, default_flow_style=False, sort_keys=False)
            
            # Post-process to convert comment keys to actual YAML comments
            module_lines = module_yaml.split('\n')
            processed_lines = []
            i = 0
            in_comment_key = False
            comment_text_parts = []
            comment_indent = 0
            
            while i < len(module_lines):
                line = module_lines[i]
                stripped = line.strip()
                
                # Check for complex key format (multi-line comment keys starting with ?)
                if stripped.startswith('?') and ("'# " in stripped or '"# ' in stripped):
                    # Start of a complex key (multi-line comment)
                    in_comment_key = True
                    comment_indent = len(line) - len(line.lstrip())
                    # Extract the first part of the comment
                    if "'# " in stripped:
                        # Find the opening quote after ?
                        quote_start = stripped.find("'")
                        if quote_start != -1:
                            # Extract from '# ' to the end of the line (may not have closing quote)
                            start_idx = stripped.find("'# ") + 1
                            if stripped.endswith("'"):
                                comment_text_parts.append(stripped[start_idx+1:-1])  # Remove quotes
                                in_comment_key = False
                                # Check if next line is ": null"
                                if i + 1 < len(module_lines) and module_lines[i + 1].strip().startswith(': null'):
                                    i += 1
                                # Write the comment
                                full_comment = " ".join(comment_text_parts)
                                processed_lines.append(" " * comment_indent + "# " + full_comment)
                                comment_text_parts = []
                            else:
                                # Multi-line, extract first part
                                comment_text_parts.append(stripped[start_idx+1:].strip())
                    elif '"# ' in stripped:
                        quote_start = stripped.find('"')
                        if quote_start != -1:
                            start_idx = stripped.find('"# ') + 1
                            if stripped.endswith('"'):
                                comment_text_parts.append(stripped[start_idx+1:-1])
                                in_comment_key = False
                                if i + 1 < len(module_lines) and module_lines[i + 1].strip().startswith(': null'):
                                    i += 1
                                full_comment = " ".join(comment_text_parts)
                                processed_lines.append(" " * comment_indent + "# " + full_comment)
                                comment_text_parts = []
                            else:
                                comment_text_parts.append(stripped[start_idx+1:].strip())
                    i += 1
                    continue
                elif in_comment_key:
                    # Continuation of multi-line comment key
                    if stripped.endswith("'") or stripped.endswith('"'):
                        # Last line of the comment
                        comment_text_parts.append(stripped.strip("'\""))
                        in_comment_key = False
                        # Skip the next line which should be ": null"
                        if i + 1 < len(module_lines) and module_lines[i + 1].strip().startswith(': null'):
                            i += 1
                        # Write the comment
                        full_comment = " ".join(comment_text_parts)
                        processed_lines.append(" " * comment_indent + "# " + full_comment)
                        comment_text_parts = []
                    else:
                        # Middle line of multi-line comment
                        comment_text_parts.append(stripped.strip("'\""))
                    i += 1
                    continue
                elif ('"# ' in stripped or "'# " in stripped) and ':' in stripped:
                    # Single-line comment key
                    if '"# ' in stripped:
                        start_idx = stripped.find('"# ') + 2
                        end_idx = stripped.find('":', start_idx)
                        if end_idx == -1:
                            end_idx = stripped.find('": null', start_idx)
                        if end_idx > start_idx:
                            comment_text = stripped[start_idx:end_idx].strip().strip('"')
                            indent = len(line) - len(line.lstrip())
                            processed_lines.append(" " * indent + "# " + comment_text)
                            i += 1
                            continue
                    elif "'# " in stripped:
                        start_idx = stripped.find("'# ") + 2
                        end_idx = stripped.find("':", start_idx)
                        if end_idx == -1:
                            end_idx = stripped.find("': null", start_idx)
                        if end_idx > start_idx:
                            comment_text = stripped[start_idx:end_idx].strip().strip("'")
                            indent = len(line) - len(line.lstrip())
                            processed_lines.append(" " * indent + "# " + comment_text)
                            i += 1
                            continue
                
                processed_lines.append(line)
                i += 1
            
            lines.extend(processed_lines)
            if not lines[-1].strip():  # Remove trailing empty line if present
                lines.pop()
            lines.append("")  # Empty line after each module
    
    # Write to file
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def generate_metadata_template(
    experiment_name: str,
    temp_module: str,
    sealevel_modules: List[str],
    experiment_path: Path,
) -> dict:
    """
    Generate metadata template with specified modules.
    
    Args:
        experiment_name: Name of the experiment
        temp_module: Name of temperature module (e.g., 'fair')
        sealevel_modules: List of sea level module names (e.g., ['bamber19-icesheets'])
        experiment_path: Path to experiment directory
    
    Returns:
        Metadata dictionary
    """
    metadata = {
        "experiment_name": 
            experiment_name,
        "pipeline-id": 
            "add your pipeline-id here",  
        "scenario": 
            "add your scenario here",  
        "baseyear": 
            "add your baseyear here",  
        "pyear_start": 
            "add your pyear_start here", 
        "pyear_end": 
            "add your pyear_end here",  
        "pyear_step": 
            "add your pyear_step here",   
        "nsamps": 
            "add your nsamps here",  
        "seed": 
            "add your seed here",   # TODO i think want this to be at module level.
        "temp_module": 
            temp_module,
        "sealevel_modules": 
            sealevel_modules if len(sealevel_modules) > 1 else sealevel_modules[0],
        "common-inputs-path": 
            "add your common-inputs-path here",
        "location-file": 
            "add your location-file here",
        "v2-output-path": 
            f"./v2_experiments/{experiment_name}/data/output",
    }
    
    # Add module-specific sections
    if temp_module == "fair":
        # Get all defaults from module dataclasses (Options, InputPaths, Inputs)
        fair_defaults = ModuleDefaultsAdapter.get_module_defaults_for_metadata("fair")
        
        # Check YAML file directly to see if input_dir is actually specified
        # (dataclass has fallback, so we need to check YAML)
        fair_defaults_yml_path = Path(__file__).parent.parent / "core" / "modules" / "fair" / "defaults.yml"
        fair_input_dir_from_yml = None
        if fair_defaults_yml_path.exists():
            with open(fair_defaults_yml_path, 'r') as f:
                fair_yml = yaml.safe_load(f) or {}
                fair_inputs_yml = fair_yml.get("inputs", {})
                # Check for fair_in_dir (dataclass field name) in YAML
                fair_input_dir_from_yml = fair_inputs_yml.get("fair_in_dir") or fair_inputs_yml.get("input_dir")
        
        # Build inputs dict, only including input_dir if it has a value in YAML
        fair_inputs = {}
        if fair_input_dir_from_yml:
            fair_inputs["input_dir"] = fair_input_dir_from_yml
        else:
            fair_inputs["input_dir"] = "add your input_dir here"
        
        # Add other input fields that have defaults
        if fair_defaults["inputs"].get("cyear_start") is not None:
            fair_inputs["cyear_start"] = fair_defaults["inputs"]["cyear_start"]
        if fair_defaults["inputs"].get("cyear_end") is not None:
            fair_inputs["cyear_end"] = fair_defaults["inputs"]["cyear_end"]
        if fair_defaults["inputs"].get("smooth_win") is not None:
            fair_inputs["smooth_win"] = fair_defaults["inputs"]["smooth_win"]
        if fair_defaults["inputs"].get("rcmip_fname"):
            fair_inputs["rcmip_fname"] = fair_defaults["inputs"]["rcmip_fname"]
        if fair_defaults["inputs"].get("param_fname"):
            fair_inputs["param_fname"] = fair_defaults["inputs"]["param_fname"]
        
        metadata["fair"] = {
            "inputs": fair_inputs,
            "options": {
                "# Options are inherited from top-level metadata (pipeline-id, nsamps, seed, scenario)": None,
                "# Module-specific options are in inputs": None,
            },
            "image": fair_defaults.get("image") or "add your image here",
            "outputs": [
                "fair/climate.nc",
                "fair/ohc.nc",
                "fair/gsat.nc",
                "fair/oceantemp.nc",
            ],
        }
    
    for sealevel_module in sealevel_modules:
        if sealevel_module == "bamber19-icesheets":
            # Get all defaults from module dataclasses (Options, InputPaths, Inputs)
            bamber_defaults = ModuleDefaultsAdapter.get_module_defaults_for_metadata("bamber19-icesheets")
            
            # Set climate_data_file to fair/climate.nc (from fair outputs)
            climate_data_file = "fair/climate.nc"
            
            metadata["bamber19-icesheets"] = {
                "inputs": {
                    "input_dir": bamber_defaults["inputs"].get("input_dir") or "add your input_dir here",
                    "replace": bamber_defaults["inputs"].get("replace"),
                    "slr_proj_mat_file": bamber_defaults["inputs"].get("slr_proj_mat_file"),
                    "climate_data_file": climate_data_file,
                },
                "options": {
                    "# Options inherited from top-level metadata: pipeline-id, nsamps, seed, scenario, pyear_start, pyear_end, pyear_step, baseyear": None,
                    "replace": bamber_defaults["options"].get("replace"),  # Bamber19-specific option from Bamber19Options
                },
                "image": bamber_defaults.get("image") or "add your image here",
                "outputs": [
                    "bamber19-icesheets/ais_gslr.nc",
                    "bamber19-icesheets/eais_gslr.nc",
                    "bamber19-icesheets/wais_gslr.nc",
                    "bamber19-icesheets/gis_gslr.nc",
                ],
            }
    
    # Remove None values to clean up the YAML, but preserve comment keys (starting with "#")
    def remove_none(d):
        """Recursively remove None values from dictionary, but preserve comment keys."""
        if isinstance(d, dict):
            return {k: remove_none(v) for k, v in d.items() if v is not None or (isinstance(k, str) and k.startswith("#"))}
        elif isinstance(d, list):
            return [remove_none(item) for item in d]
        else:
            return d
    
    return remove_none(metadata)


def create_experiment_directory(
    experiment_name: str,
    temp_module: str,
    sealevel_modules: List[str],
    project_root: Path = None,
):
    """
    Create a new experiment directory with template files.
    
    Args:
        experiment_name: Name of the experiment (will be the directory name)
        temp_module: Name of temperature module (e.g., 'fair')
        sealevel_modules: List of sea level module names (e.g., ['bamber19-icesheets'])
        project_root: Root directory of the project (defaults to finding directory with pyproject.toml)
    """
    if project_root is None:
        # Find project root by looking for pyproject.toml
        project_root = find_project_root()
        print(f"project_root: {project_root}")
    
    experiments_dir = project_root / "v2_experiments"
    experiment_path = experiments_dir / experiment_name
    
    # Check if directory already exists
    if experiment_path.exists():
        print(f"Error: Directory {experiment_path} already exists")
        sys.exit(1)
    
    # Create directory
    experiment_path.mkdir(parents=True)
    print(f"✓ Created directory: {experiment_path}")
    
    # Create data directory structure
    data_dir = experiment_path / "data" / "v2_output_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created data/v2_output_data directory")
    
    # Generate metadata file
    metadata = generate_metadata_template(
        experiment_name, temp_module, sealevel_modules, experiment_path
    )
    
    metadata_path = experiment_path / "v2-experiment-metadata.yml"
    write_metadata_yaml(metadata, metadata_path)
    print(f"✓ Created v2-experiment-metadata.yml")
    
    # Copy README template if it exists (check both README and README.md)
    readme_template = experiments_dir / "templates" / "README.md"
    if not readme_template.exists():
        readme_template = experiments_dir / "templates" / "README"
    
    if readme_template.exists():
        readme_path = experiment_path / "README.md"
        content = readme_template.read_text()
        content = content.replace("experiment-name", experiment_name)
        readme_path.write_text(content)
        print(f"✓ Created README.md")
    else:
        print(f"⚠ Warning: README template not found at {experiments_dir / 'templates' / 'README.md'} or {experiments_dir / 'templates' / 'README'}")
    
    print(f"\n✨ Experiment directory setup complete!")
    print(f"\nNext steps:")
    print(f"  1. Edit {metadata_path}")
    print(f"     - Fill in all placeholder values (pipeline-id, scenario, paths, etc.)")
    print(f"  2. Generate Docker Compose:")
    print(f"     uv run generate-compose {experiment_path}")


def main():
    """Main entry point for the setup_new_experiment script."""
    if len(sys.argv) < 4:
        print("Usage: setup-new-experiment <experiment_name> <temp_module> <sealevel_module> [<sealevel_module2> ...]")
        print("Example: setup-new-experiment my_new_experiment fair bamber19-icesheets")
        print("Example: setup-new-experiment my_new_experiment fair bamber19-icesheets ipccar5")
        sys.exit(1)
    
    experiment_name = sys.argv[1]
    temp_module = sys.argv[2]
    sealevel_modules = sys.argv[3:]
    
    create_experiment_directory(experiment_name, temp_module, sealevel_modules)


if __name__ == "__main__":
    main()

