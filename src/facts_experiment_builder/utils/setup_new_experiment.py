"""Jinja2-based YAML generation for experiment metadata files.

This module provides Jinja2 templating for generating experiment-metadata.yml files.
It can be used as a self-contained module for Jinja2-based experiment setup.

STRUCTURE:
The setup process is broken into three functions:
1. create_experiment_directory() - Creates the experiment directory
2. create_experiment_directory_files() - Creates data directories and README
3. generate_metadata_template() - Generates metadata dictionary structure
4. populate_metadata_with_defaults() - Populates defaults from defaults.yml files
5. write_metadata_yaml_jinja2() - Writes metadata to YAML using Jinja2 templating

CLI ARGUMENT HANDLING:
The generate_metadata_template() function optionally accepts CLI arguments
(pipeline_id, scenario, baseyear, etc.). When provided, these values are passed to
create_metadata_bundle() which creates metadata bundles with:
- clue: Comment text (always shown)
- value: The CLI-provided value (shown if provided, blank line if None)

The format_yaml_value() function handles this by:
- Always rendering the clue as a comment line
- Only rendering the value line if value is not None

NOTE:
This module is completely independent from setup_new_experiment.py. It contains
all necessary functions for generating and writing experiment metadata using
Jinja2 templating. This allows it to be used as a standalone alternative.
"""

import sys
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from jinja2 import Environment, BaseLoader
try:
    from markupsafe import Markup
except ImportError:
    # Fallback for older Jinja2 versions
    from jinja2 import Markup


# Jinja2 template for experiment metadata YAML
# Reverse-engineered from v2_experiments/epa_experiment/experiment-metadata.yml
YAML_TEMPLATE = """
### Experiment metadata YAML file ###
# This is the main configuration file that describes the specified FACTS experiment. 
# It is generated with prepopulated keys based on the modules you specified in `setup-new-experiment`. 
# The values included here are defaults based on the default values for each module specified in /modules/module_name/defaults.yml.

# **How to use this file:**
# 1. Fill in the desired values for the top-level parameters of the experiment.
# 2. Specify the location of the input data to be used in this experiment.
# 3. Specify the location file to be used in this experiment.
# 4. Review the module-level inputs, options, and outputs to ensure they are correct.

# **IMPORTANT**
# This file does not 'run' a FACTS experiment, it merely specifies an experiment. Once you have completed filling out this file, run:
# `uv run generate-compose <experiment_directorY> to generate a Docker Compose file that corresponds to this experiment.
# Then, run `docker compose -f <compose_file> up` to run the experiment.

experiment_name:
{{ format_value(metadata.experiment_name) }}

##----- Top-level params -----##
{% for key in top_level_params %}
{% if key in metadata %}
{{ key }}:
{{ format_value(metadata[key]) }}
{% endif %}
{% endfor %}

##----- Modules included in experiment -----##
{% for module_key in included_modules %}
{% if module_key in metadata %}
{{ module_key }}:
{{ format_value(metadata[module_key]) }}
{% endif %}
{% endfor %}

##----- Inputs -----##
{% for key in inputs %}
{% if key in metadata %}
{{ key }}:
{{ format_value(metadata[key]) }}
{% endif %}
{% endfor %}

##----- Outputs -----##
{% for key in outputs %}
{% if key in metadata %}
{{ key }}:
{{ format_value(metadata[key]) }}
{% endif %}
{% endfor %}

##----- Module-specific inputs, options, and outputs -----##
{% for module_key in module_keys %}
{{ module_key }}:
{{ format_module(module_key, metadata[module_key]) }}
{% endfor %}
"""


def is_metadata_value(obj: Any) -> bool:
    """
    Check if an object is a metadata value dict (has 'clue' key, 'value' is optional).
    
    Args:
        obj: Object to check
        
    Returns:
        True if obj is a metadata value dict, False otherwise
    """
    return isinstance(obj, dict) and "clue" in obj


def format_yaml_value(value: Any) -> str:
    """
    Format a YAML value with clue/value dict structure.
    
    Handles metadata values created by create_metadata_bundle() which can optionally
    include values passed from CLI arguments. The format is:
    - {"clue": "Comment text", "value": <value or None>}
    
    When value is None (not provided from CLI):
        # Comment text
        (blank line)
    
    When value is provided from CLI:
        # Comment text
        <value>
    
    Args:
        value: Value to format (clue/value dict, or simple value for special cases like experiment_name)
        
    Returns:
        Formatted string representation (with proper indentation for template)
    """
    # Handle simple values (like experiment_name, temperature_module, sealevel_modules)
    if not is_metadata_value(value):
        return format_simple_value(value)
    
    # Handle clue/value dicts (created by create_metadata_bundle())
    clue = value.get("clue")
    cli_value = value.get("value")  # Value passed from CLI, or None if not provided
    
    # Format clue as comment (8 spaces indentation to match other values)
    result = f"        # {clue}"
    
    # Format CLI-provided value if it exists (otherwise just blank line after comment)
    if cli_value is not None:
        formatted_value = format_simple_value(cli_value)
        result += "\n" + formatted_value
    
    return result


def format_simple_value(value: Any) -> str:
    """
    Format a simple YAML value (not a metadata value dict).
    
    Args:
        value: Simple value to format
        
    Returns:
        Formatted string with proper indentation (8 spaces to match other values)
    """
    if isinstance(value, str):
        # Quote strings that contain special characters or start with $
        if value.startswith("$") or " " in value or "/" in value:
            return f'        "{value}"'
        return f"        {value}"
    elif isinstance(value, list):
        # Format list items with proper indentation (8 spaces to match other values)
        if not value:
            return "        []"
        result = []
        for item in value:
            result.append(f"        - {item}")
        return "\n".join(result)
    else:
        return f"        {value}"


def format_module_value(key: str, value: Any, indent: int = 2) -> List[str]:
    """
    Format a single key-value pair in a module section, handling clue/value dicts.
    
    Handles clue/value dicts created by create_metadata_bundle() where the value
    can be None if not provided from CLI. In that case, only the clue comment
    is rendered (with blank line after).
    
    Args:
        key: Key name
        value: Value (can be clue/value dict, regular dict, list, or simple value)
        indent: Indentation level in spaces
        
    Returns:
        List of formatted lines
    """
    lines = []
    indent_str = " " * indent
    
    if is_metadata_value(value):
        # Clue/value dict: render clue as comment, CLI-provided value below if it exists
        clue = value.get("clue", "")
        cli_value = value.get("value")  # Value from CLI, or None if not provided
        lines.append(f"{indent_str}{key}:")
        lines.append(f"{indent_str}  # {clue}")
        if cli_value is not None:
            # Format the CLI-provided value
            if isinstance(cli_value, str):
                if cli_value.startswith("$") or " " in cli_value or "/" in cli_value:
                    lines.append(f'{indent_str}  "{cli_value}"')
                else:
                    lines.append(f"{indent_str}  {cli_value}")
            elif isinstance(cli_value, list):
                for item in cli_value:
                    lines.append(f"{indent_str}  - {item}")
            else:
                lines.append(f"{indent_str}  {cli_value}")
        # If cli_value is None, no value line is added (blank line after comment)
    elif isinstance(value, dict):
        # Regular nested dict (like inputs, options, outputs sections)
        lines.append(f"{indent_str}{key}:")
        for nested_key, nested_value in value.items():
            if nested_key.startswith("#"):
                # Comment key
                lines.append(f"{indent_str}  {nested_key}")
            else:
                nested_lines = format_module_value(nested_key, nested_value, indent + 2)
                lines.extend(nested_lines)
    elif isinstance(value, list):
        # List value (like sealevel_modules)
        lines.append(f"{indent_str}{key}:")
        for item in value:
            lines.append(f"{indent_str}  - {item}")
    else:
        # Simple value (like image string, temperature_module string)
        if isinstance(value, str) and (value.startswith("$") or " " in value or "/" in value):
            lines.append(f'{indent_str}{key}: "{value}"')
        else:
            lines.append(f"{indent_str}{key}: {value}")
    
    return lines


def format_module(module_key: str, module_data: Dict[str, Any]) -> str:
    """
    Format a module section with comment handling and clue/value support.
    
    Uses 2-space indentation to match the actual YAML file format.
    Handles clue/value dicts by rendering clues as comments.
    
    Args:
        module_key: Module name/key
        module_data: Module data dictionary
        
    Returns:
        Formatted YAML string for the module (without the module key line, as template adds it)
    """
    lines = []
    
    for key, value in module_data.items():
        if key.startswith("#"):
            # Comment key
            lines.append(f"  {key}")
        else:
            formatted_lines = format_module_value(key, value, indent=2)
            lines.extend(formatted_lines)
    
    return "\n".join(lines)


def write_metadata_yaml_jinja2(metadata: dict, output_path: Path):
    """
    Write metadata to YAML file using Jinja2 templating.
    
    This function is called by prepopulate_experiment_metadata_file() to write
    the generated metadata dictionary to experiment-metadata.yml.
    
    The metadata dictionary contains:
    - Top-level params: Created with create_metadata_bundle(clue, value) where
      value can be None if not provided from CLI
    - Module sections: Module-specific inputs, options, and outputs
    - Input/output paths: module-specific-input-data, general-input-data, location-file-name, output-data-location
    
    Args:
        metadata: Metadata dictionary generated by generate_metadata_template()
        output_path: Path to output YAML file (typically experiment-metadata.yml)
    """
    # Define sections
    top_level_params = [
        "pipeline-id", "scenario", "baseyear", "pyear_start", "pyear_end",
        "pyear_step", "nsamps", "seed"
    ]
    
    # Included modules (temperature_module and sealevel_modules)
    # These are the keys that appear in the "Modules included in experiment" section
    included_modules = []
    if "temperature_module" in metadata:
        included_modules.append("temperature_module")
    if "sealevel_modules" in metadata:
        included_modules.append("sealevel_modules")
    
    # Inputs section (module-specific-input-data, general-input-data, location-file-name)
    inputs = []
    if "module-specific-input-data" in metadata:
        inputs.append("module-specific-input-data")
    if "general-input-data" in metadata:
        inputs.append("general-input-data")
    if "location-file-name" in metadata:
        inputs.append("location-file-name")
    
    # Outputs section (output-data-location)
    outputs = []
    if "output-data-location" in metadata:
        outputs.append("output-data-location")
    
    # Module-specific sections (all keys that are module names)
    # Exclude top-level params, included_modules, inputs, outputs, and experiment_name
    excluded_keys = set(top_level_params + included_modules + inputs + outputs + ["experiment_name"])
    module_keys = [
        key for key in metadata.keys() 
        if key not in excluded_keys and isinstance(metadata[key], dict)
    ]
    
    # Sort module_keys so temperature_module appears first if it exists
    if "temperature_module" in metadata:
        temperature_module_name = metadata.get("temperature_module")
        if temperature_module_name and isinstance(temperature_module_name, str) and temperature_module_name.upper() != "NONE":
            if temperature_module_name in module_keys:
                module_keys.remove(temperature_module_name)
                module_keys.insert(0, temperature_module_name)
    
    # Create Jinja2 environment
    env = Environment(
        loader=BaseLoader(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    # Add custom functions and filters
    def format_value(value):
        result = format_yaml_value(value)
        # Return as Markup to prevent Jinja2 from escaping
        return Markup(result)
    
    def format_module_func(key, data):
        result = format_module(key, data)
        return Markup(result)
    
    env.globals['format_value'] = format_value
    env.globals['format_module'] = format_module_func
    # Also add as filter for alternative syntax
    env.filters['format_value'] = format_value
    
    # Create template
    template = env.from_string(YAML_TEMPLATE)
    
    # Render template
    try:
        rendered = template.render(
            metadata=metadata,
            top_level_params=top_level_params,
            included_modules=included_modules,
            inputs=inputs,
            outputs=outputs,
            module_keys=module_keys,
        )
    except Exception as e:
        raise ValueError(f"Error rendering Jinja2 template: {e}") from e
    
    # Write to file
    with open(output_path, "w") as f:
        f.write(rendered)


# ============================================================================
# Independent implementation - no dependencies on setup_new_experiment.py
# ============================================================================

# Mapping of top-level param keys to their clue/help text
TOP_LEVEL_PARAM_CLUES = {
    "pipeline-id": "Pipeline ID",
    "scenario": "Emissions scenario name",
    "baseyear": "Base year",
    "pyear_start": "Projection year start",
    "pyear_end": "Projection year end",
    "pyear_step": "Projection year step",
    "nsamps": "Number of samples",
    "seed": "Random seed to use for sampling",
    "module-specific-input-data": "Module-specific input data",
    "general-input-data": "General input data",
    "location-file-name": "Location file name",
    "output-data-location": "Output path",
}

def create_metadata_clue(clue: str) -> Dict[str, str]:
    """Create a metadata clue dictionary."""
    return {"clue": clue}

def create_metadata_value(value: Any = None) -> Dict[str, Any]:
    """Create a metadata value dictionary."""
    return {"value": value}

def create_metadata_bundle(clue: str, value: Any = None) -> Dict[str, Any]:
    """Create a metadata bundle with clue and optional value."""
    return {"clue": clue, "value": value}

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
        f"Could not find pyproject.toml starting from {start_path}. "
        "Please run this script from within the project directory."
    )

@dataclass
class ModuleYamlAbs:
    """Dataclass representing the structure of a module.yaml file."""
    module_name: str
    container_image: str
    arguments: Dict[str, List[Dict[str, Any]]]  # Keys: "top_level", "options", "inputs", "outputs"
    volumes: Dict[str, Dict[str, Any]]
    depends_on: Optional[List[Dict[str, Any]]] = None  # Optional field
    
    @classmethod
    def _find_module_yaml(cls, module_name: str) -> Path:
        """
        Find the module YAML file for a given module name.
        
        Args:
            module_name: The module name (e.g., 'fair', 'bamber19-icesheets')
            
        Returns:
            Path to the module YAML file
            
        Raises:
            FileNotFoundError: If the module YAML file cannot be found

        TODO this will need to be updated when we move the module yamls.
        """
        # Get the modules directory (flat structure, no subdirectories)
        project_root = Path(__file__).parent.parent.parent.parent
        modules_dir = project_root / "src" / "facts_experiment_builder" / "core" / "modules"
        
        # Convert module name to filename format
        module_dir_name = module_name.replace('-', '_')
        
        possible_paths = [
            modules_dir / f"{module_dir_name}_module.yaml",
            modules_dir / f"{module_name}_module.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # If not found, raise error
        raise FileNotFoundError(
            f"Module YAML file not found for module name '{module_name}'. "
            f"Tried paths: {[str(p) for p in possible_paths]}"
        )
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'ModuleYamlAbs':
        """
        Create a ModuleYamlAbs instance from a YAML file.
        
        Args:
            yaml_path: Path to the module YAML file
            
        Returns:
            ModuleYamlAbs instance
        """
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return cls(
            module_name=data['module_name'],
            container_image=data['container_image'],
            arguments=data.get('arguments', {}),
            volumes=data.get('volumes', {}),
            depends_on=data.get('depends_on')
        )
    
    @classmethod
    def from_module_name(cls, module_name: str) -> 'ModuleYamlAbs':
        """
        Create a ModuleYamlAbs instance from a module name by finding and loading the YAML file.
        
        Args:
            module_name: The module name (e.g., 'fair', 'bamber19-icesheets')
            
        Returns:
            ModuleYamlAbs instance
        """
        yaml_path = cls._find_module_yaml(module_name)
        return cls.from_yaml(yaml_path)

def get_clue_from_module_yaml(module_yaml: ModuleYamlAbs, arg_type: str, field_name: str) -> str:
    """
    Extract clue/help text from module.yaml for a specific field.
    
    Args:
        module_yaml: ModuleYamlAbs instance
        arg_type: Type of argument ('options', 'inputs', 'outputs', 'top_level')
        field_name: Field name to look up
        
    Returns:
        Help text from module.yaml, or fallback clue if not found
    """
    # Look through arguments of the specified type
    arg_specs = module_yaml.arguments.get(arg_type, [])
    
    for arg_spec in arg_specs:
        # Check if this arg_spec matches the field_name
        source = arg_spec.get("source", "")
        if "." in source:
            source_field = source.split(".")[-1]
            if source_field == field_name:
                # Found matching arg_spec, check for help field
                help_text = arg_spec.get("help", "")
                if help_text:
                    return help_text
    
    # Fallback: generate clue from field name
    return f"add your {field_name} here"

def get_module_defaults_path(module_name: str) -> Optional[Path]:
    """Get the path to the defaults.yml file for a module."""
    mod_defaults_name = f"defaults_{module_name.replace('-', '_')}.yml"
    defaults_yml_path = Path(__file__).parent.parent / "core" / "modules" / mod_defaults_name
    if defaults_yml_path.exists():
        return defaults_yml_path
    else:
        return None

def read_defaults_yml(module_name: str) -> dict:
    """Read defaults from defaults.yml file for a module."""
    defaults_yml_path = get_module_defaults_path(module_name)
    if defaults_yml_path:
        with open(defaults_yml_path, 'r') as f:
            defaults_yml = yaml.safe_load(f) or {}
        return defaults_yml
    else:
        return {}

def populate_metadata_with_defaults(metadata: dict, module_name: str) -> dict:
    """
    Populate metadata with defaults from defaults.yml files, preserving clues.
    
    This function:
    - Creates missing sections (inputs, options) if they don't exist
    - Preserves existing clues when updating values
    - Adds missing fields from defaults
    - Handles comment keys in options section (keys starting with "#")
    
    Args:
        metadata: Metadata dictionary
        module_name: Name of the module to populate defaults for (e.g., "fair-temperature", "bamber19-icesheets")
    
    Returns:
        Updated metadata dictionary
    TODO this will ahve to change once we move the module yamls.
    """
    defaults_yml = read_defaults_yml(module_name)
    
    if not defaults_yml:
        # No defaults file found, return unchanged
        return metadata
    
    # Ensure module section exists
    if module_name not in metadata:
        metadata[module_name] = {}
    
    # Try to get module YAML for clues (optional, may not exist for all modules)
    module_yaml = None
    try:
        
        module_yaml = ModuleYamlAbs.from_module_name(module_name)
    except (FileNotFoundError, Exception):
        # Module YAML not found, will use fallback clues
        pass
    
    for section_key, section_defaults in defaults_yml.items():
        # section_key is like "options", "inputs", "image"
        
        # Ensure section exists in metadata
        if section_key not in metadata[module_name]:
            if section_key in ["inputs", "options"]:
                metadata[module_name][section_key] = {}
            elif section_key == "image":
                metadata[module_name][section_key] = ""
            else:
                continue
        
        current_section = metadata[module_name][section_key]
        
        # Handle nested structures (inputs, options)
        if isinstance(section_defaults, dict) and isinstance(current_section, dict):
            # Filter out comment keys (keys starting with "#") when iterating
            # But preserve them in the final structure
            comment_keys = {k: v for k, v in current_section.items() if isinstance(k, str) and k.startswith("#")}
            
            # Update each nested key-value pair from defaults
            for nested_key, nested_default in section_defaults.items():
                # Try to find matching key in metadata (handle kebab-case vs snake_case)
                # First try exact match
                matching_key = None
                if nested_key in current_section:
                    matching_key = nested_key
                else:
                    # Try converting kebab-case to snake_case
                    snake_case_key = nested_key.replace("-", "_")
                    if snake_case_key in current_section:
                        matching_key = snake_case_key
                    else:
                        # Try converting snake_case to kebab-case
                        kebab_case_key = nested_key.replace("_", "-")
                        if kebab_case_key in current_section:
                            matching_key = kebab_case_key
                
                if matching_key:
                    nested_current = current_section[matching_key]
                    # Current value should be a metadata value dict, update its value
                    if is_metadata_value(nested_current):
                        # Preserve existing clue, update value
                        nested_current["value"] = nested_default
                    elif nested_current is None or nested_current == "":
                        # Empty value, try to get clue from module YAML or use fallback
                        clue = None
                        if module_yaml:
                            # Try to get clue from module YAML (use matching_key for lookup)
                            if section_key == "inputs":
                                clue = get_clue_from_module_yaml(module_yaml, "inputs", matching_key)
                            elif section_key == "options":
                                clue = get_clue_from_module_yaml(module_yaml, "options", matching_key)
                        if not clue:
                            clue = f"add your {matching_key} here"
                        current_section[matching_key] = create_metadata_bundle(clue, nested_default)
                    else:
                        # Not a metadata value dict, replace with metadata bundle
                        clue = f"add your {matching_key} here"
                        current_section[matching_key] = create_metadata_bundle(clue, nested_default)
                else:
                    # New key not in metadata, add it with default value
                    # Prefer snake_case to match metadata structure (from module YAML sources)
                    # But check if kebab-case version already exists (from previous runs)
                    snake_case_key = nested_key.replace("-", "_")
                    kebab_case_key = nested_key.replace("_", "-") if "_" in nested_key else nested_key
                    
                    # Check if either format already exists (might be from previous population)
                    if snake_case_key in current_section:
                        # Snake_case version exists, update it
                        matching_key = snake_case_key
                        nested_current = current_section[matching_key]
                        if is_metadata_value(nested_current):
                            nested_current["value"] = nested_default
                        else:
                            clue = f"add your {matching_key} here"
                            current_section[matching_key] = create_metadata_bundle(clue, nested_default)
                    elif kebab_case_key in current_section and kebab_case_key != nested_key:
                        # Kebab-case version exists, update it
                        matching_key = kebab_case_key
                        nested_current = current_section[matching_key]
                        if is_metadata_value(nested_current):
                            nested_current["value"] = nested_default
                        else:
                            clue = f"add your {matching_key} here"
                            current_section[matching_key] = create_metadata_bundle(clue, nested_default)
                    else:
                        # Neither exists, add new key using snake_case to match metadata structure
                        clue = None
                        if module_yaml:
                            # Try both original key and snake_case version for clue lookup
                            if section_key == "inputs":
                                clue = get_clue_from_module_yaml(module_yaml, "inputs", snake_case_key)
                                if not clue:
                                    clue = get_clue_from_module_yaml(module_yaml, "inputs", nested_key)
                            elif section_key == "options":
                                clue = get_clue_from_module_yaml(module_yaml, "options", snake_case_key)
                                if not clue:
                                    clue = get_clue_from_module_yaml(module_yaml, "options", nested_key)
                        if not clue:
                            clue = f"add your {snake_case_key} here"
                        current_section[snake_case_key] = create_metadata_bundle(clue, nested_default)
            
            # Restore comment keys
            for comment_key, comment_value in comment_keys.items():
                if comment_key not in current_section:
                    current_section[comment_key] = comment_value
        
        elif section_key == "image" and isinstance(section_defaults, dict):
            # Handle image as a special case - it's stored as a string
            image_url = section_defaults.get("image_url")
            if image_url:
                metadata[module_name][section_key] = image_url
    
    return metadata

def format_module_from_yaml(module_yaml: ModuleYamlAbs) -> dict:
    #First build inputs dict
    module_inputs = {}
    for arg_spec in module_yaml.arguments.get("inputs", []):
        arg_name = arg_spec.get("name", "")
        source = arg_spec.get("source", "")
        if "." in source:
            field_name = source.split(".")[-1]
            clue = get_clue_from_module_yaml(module_yaml, "inputs", field_name)
            if field_name == "climate_data_file":
                module_inputs[field_name] = create_metadata_bundle(clue, "fair/climate.nc") #TODO will need to fix this.
            else:
                module_inputs[field_name] = create_metadata_bundle(clue)

    #Then build options dict
    module_options = {}
    top_level_args = module_yaml.arguments.get("top_level", [])
    top_level_names = [arg.get("name", "") for arg in top_level_args]
    if top_level_names:
        top_level_str = ", ".join(top_level_names)
        module_options[f"# Options inherited from top-level metadata: {top_level_str}"] = None

    #add module-specific options
    for arg_spec in module_yaml.arguments.get("options", []):
        arg_name = arg_spec.get("name", "")
        source = arg_spec.get("source", "")
        if "." in source:
            field_name = source.split(".")[-1]
            clue = get_clue_from_module_yaml(module_yaml, "options", field_name)
            module_options[field_name] = create_metadata_bundle(clue)

    #build outputs dict
    module_outputs = {}
    for arg_spec in module_yaml.arguments.get("outputs", []):
        arg_name = arg_spec.get("name", "")
        if not arg_name:
            continue #TODO there's def a better way to handle the next section.
        if arg_name.startswith("output-") and arg_name.endswith("-file"):
            output_name = arg_name[7:-5]
            module_outputs[arg_name] = f"{module_yaml.module_name}/{output_name}.nc"
        else:
            output_name = arg_name.replace("-", "_")
            module_outputs[arg_name] = f"{module_yaml.module_name}/{output_name}.nc"

    module_dict = {
        "inputs": module_inputs,
        "options": module_options,
        "image": module_yaml.container_image,
        "outputs": module_outputs,
    }
    return module_dict
   
def generate_metadata_template(
    experiment_name: str,
    temperature_module: str,
    sealevel_modules: List[str],
    experiment_path: Path,
    pipeline_id: str = None,
    scenario: str = None,
    baseyear: int = None,
    pyear_start: int = None,
    pyear_end: int = None,
    pyear_step: int = None,
    nsamps: int = None,
    seed: int = None,
    ) -> dict:
    """
    Generate metadata template with specified modules.
    
    Args:
        experiment_name: Name of the experiment
        temperature_module: Name of temperature module (e.g., 'fair')
        sealevel_modules: List of sea level module names (e.g., ['bamber19-icesheets'])
        experiment_path: Path to experiment directory
        pipeline_id: Optional pipeline ID from CLI
        scenario: Optional scenario from CLI
        baseyear: Optional base year from CLI
        pyear_start: Optional projection year start from CLI
        pyear_end: Optional projection year end from CLI
        pyear_step: Optional projection year step from CLI
        nsamps: Optional number of samples from CLI
        seed: Optional seed from CLI
    
    Returns:
        Metadata dictionary
    """
    # Create metadata bundles with clue and optional value
    # If value is passed from CLI, it will be included; otherwise value will be None (blank line)
    metadata = {
        "experiment_name": 
            experiment_name,
        "pipeline-id": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("pipeline-id", "Pipeline ID"),
                pipeline_id
            ),
        "scenario": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("scenario", "Emissions scenario name"),
                scenario
            ),
        "baseyear": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("baseyear", "Base year"),
                baseyear
            ),
        "pyear_start": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("pyear_start", "Projection year start"),
                pyear_start
            ),
        "pyear_end": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("pyear_end", "Projection year end"),
                pyear_end
            ),
        "pyear_step": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("pyear_step", "Projection year step"),
                pyear_step
            ),
        "nsamps": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("nsamps", "Number of samples"),
                nsamps
            ),
        "seed": 
            create_metadata_bundle(
                TOP_LEVEL_PARAM_CLUES.get("seed", "Random seed to use for sampling"),
                seed
            ),
        "temperature_module": 
            temperature_module,
        "sealevel_modules": 
            sealevel_modules if len(sealevel_modules) > 1 else sealevel_modules[0],
        "module-specific-input-data": 
            create_metadata_bundle("Module-specific input data"),
        "general-input-data": 
            create_metadata_bundle("General input data"),
        "location-file-name": 
            create_metadata_bundle("Location file name"),
        "output-data-location": 
            create_metadata_bundle(TOP_LEVEL_PARAM_CLUES.get("output-data-location", "Output path"), 
                                 f"./v2_experiments/{experiment_name}/data/output"),
    }
    # Add module-specific sections for temp module
    if temperature_module and temperature_module.upper() != "NONE":
        try:
            temperature_module_yaml = ModuleYamlAbs.from_module_name(temperature_module)
        except Exception as e:
            print(f"Error trying to generate metadata template from temperature module yaml: {e}")

        metadata[temperature_module] = format_module_from_yaml(temperature_module_yaml)
        
            

    # Add sealevel module sections
    for sealevel_module in sealevel_modules:
        try:
            sealevel_module_yaml = ModuleYamlAbs.from_module_name(sealevel_module)

            sealevel_module_dict = format_module_from_yaml(sealevel_module_yaml)
            metadata[sealevel_module] = sealevel_module_dict
        except Exception as e:
            print(f"Error trying to generate metadata template from {sealevel_module} module yaml: {e}")
    

    # TODO: Add framework modules (if exist)
    # TODO: Add esl modules (if exist)

    
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
    project_root: Path = None,
    ) -> Path:
    """
    Create a new experiment directory.
    
    Args:
        experiment_name: Name of the experiment (will be the directory name)
        project_root: Root directory of the project (defaults to finding directory with pyproject.toml)
        
    Returns:
        Path to the created experiment directory
    """
    if project_root is None:
        project_root = find_project_root()
    
    experiments_dir = project_root / "v2_experiments"
    experiment_path = experiments_dir / experiment_name
    
    # Check if directory already exists
    if experiment_path.exists():
        print(f"Error: Directory {experiment_path} already exists")
        sys.exit(1)
    
    # Create directory
    experiment_path.mkdir(parents=True)
    print(f"✓ Created directory: {experiment_path}")
    return experiment_path

def create_experiment_directory_files(experiment_path: Path):
    """
    Create data directories and README file for an experiment.
    
    Args:
        experiment_path: Path to experiment directory
    """
    # Create data directory structure
    data_dir = experiment_path / "data" / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created data/output directory")
    
    # Copy README template if it exists
    experiments_dir = experiment_path.parent
    readme_template = experiments_dir / "README.md"
    if readme_template.exists():
        readme_path = experiment_path / "README.md"
        shutil.copy(readme_template, readme_path)
        print(f"✓ Created README.md")
    else:
        print(f"⚠ Warning: README template not found at {experiments_dir / 'README.md'}")

