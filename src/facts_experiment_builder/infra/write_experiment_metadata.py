from pathlib import Path
from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.core.components.metadata_bundle import is_metadata_value
from typing import Any, List, Dict
from jinja2 import Environment, BaseLoader

try:
    from markupsafe import Markup
except ImportError:
    # Fallback for older Jinja2 versions
    from jinja2 import Markup

# Jinja2 template for experiment metadata YAML
YAML_TEMPLATE = """
### Experiment configuration YAML file ###
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

# About this experiment:
# Date created: {{ experiment.date_created}}
# Module registry version: {{ module_registry_version or "unknown" }}
experiment_name:
{{ format_value(experiment.experiment_name) }}

##----- Top-level params -----##
{% for key, value in experiment.top_level_params.items() %}
{{ key }}:
{{ format_value(value) }}
{% endfor %}

##----- Modules included in experiment -----##
{% for module_key in included_modules %}
{% if module_key in manifest %}
{{ module_key }}:
{{ format_value(manifest[module_key]) }}
{% endif %}
{% endfor %}

##----- Workflows (facts-total) -----##
{% if experiment.workflows %}
workflows:
{% for wf_name, wf_modules in experiment.workflows.items() %}
  {{ wf_name }}: "{{ wf_modules }}"
{% endfor %}
{% endif %}

##----- Inputs -----##
{% for key in inputs %}
{% if key in experiment.paths %}
{{ key }}:
{{ format_value(experiment.paths[key]) }}
{% endif %}
{% endfor %}

##----- Outputs -----##
{% for key in outputs %}
{% if key in experiment.paths %}
{{ key }}:
{{ format_value(experiment.paths[key]) }}
{% endif %}
{% endfor %}


##--------------------------------------------------------##
##--------------------------------------------------------##
##----- Module-specific inputs, options, and outputs -----##
{% for module_key in module_keys %}
{{ module_key }}:
{{ format_module(module_key, module_sections[module_key]) }}
{% endfor %}
"""


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
        clue = value.get("clue", "")
        cli_value = value.get("value")
        default_value = value.get("default_value", "")
        filename = value.get("filename", "")
        lines.append(f"{indent_str}{key}:")
        lines.append(f"{indent_str}  # {clue}")
        if cli_value is not None:
            if isinstance(cli_value, str):
                if cli_value.startswith("$") or " " in cli_value or "/" in cli_value:
                    lines.append(f'{indent_str}  "{cli_value}"  # user specified value')
                else:
                    lines.append(f"{indent_str}  {cli_value}  # user specified value")
            elif isinstance(cli_value, list):
                for item in cli_value:
                    lines.append(f"{indent_str}  - {item}")
            else:
                lines.append(f"{indent_str}  {cli_value}  # user specified value")
        elif filename:
            if isinstance(filename, str) and ("/" in filename or " " in filename):
                lines.append(
                    f'{indent_str}  "{filename}"  # filename from module defaults'
                )
            else:
                lines.append(
                    f"{indent_str}  {filename}  # filename from module defaults"
                )
        elif default_value:
            if isinstance(default_value, str) and (
                default_value.startswith("$")
                or " " in default_value
                or "/" in default_value
            ):
                lines.append(
                    f'{indent_str}  "{default_value}"  # value from module defaults'
                )
            else:
                lines.append(
                    f"{indent_str}  {default_value}  # value from module defaults"
                )
    elif isinstance(value, dict):
        # Regular nested dict (like inputs, options, outputs sections)
        lines.append(f"{indent_str}{key}:")
        for nested_key, nested_value in value.items():
            if nested_key.startswith("#"):
                # Comment key
                lines.append(f"{indent_str}  {nested_key}")
            else:
                nested_lines = format_module_value(
                    nested_key, nested_value, indent=indent + 2
                )
                lines.extend(nested_lines)
    elif isinstance(value, list):
        # List value (like sealevel_modules)
        lines.append(f"{indent_str}{key}:")
        for item in value:
            lines.append(f"{indent_str}  - {item}")
    else:
        # Simple value (like image string, temperature_module string)
        if isinstance(value, str) and (
            value.startswith("$") or " " in value or "/" in value
        ):
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


def write_metadata_yaml_jinja2(
    experiment: FactsExperiment,
    output_path: Path,
    module_registry_version: str | None = None,
):
    """
    Write metadata to YAML file using Jinja2 templating.

    Accepts a FactsExperiment.

    Args:
        experiment: FactsExperiment
        output_path: Path to output YAML file (typically experiment-config.yaml)
    """
    # Build manifest and module_sections from steps
    fw = (
        [experiment.totaling_step.module_name]
        if experiment.totaling_step.is_present
        else []
    )
    esl = (
        [experiment.extreme_sealevel_step.module_name]
        if experiment.extreme_sealevel_step.is_present
        else []
    )
    manifest = {
        "temperature_module": experiment.climate_step.module_name or "NONE",
        "sealevel_modules": experiment.sealevel_step.module_names,
        "framework_modules": fw,
        "esl_modules": esl,
    }
    module_sections: Dict[str, Any] = {}
    for step in experiment.list_all_steps():
        for spec in step.module_specs():
            module_sections[spec.module_name] = spec.to_dict()

    # Included modules (temperature_module, sealevel_modules, framework_modules, esl_modules)
    # These are the keys that appear in the "Modules included in experiment" section
    included_modules = []
    if "temperature_module" in manifest:
        included_modules.append("temperature_module")
    if "sealevel_modules" in manifest:
        included_modules.append("sealevel_modules")
    if "framework_modules" in manifest and manifest["framework_modules"]:
        included_modules.append("framework_modules")
    if "esl_modules" in manifest and manifest["esl_modules"]:
        included_modules.append("esl_modules")

    # Inputs section (module-specific-input-data, shared-input-data, location-file-name)
    inputs = []
    if "module-specific-input-data" in experiment.paths:
        inputs.append("module-specific-input-data")
    if "shared-input-data" in experiment.paths:
        inputs.append("shared-input-data")
    if "experiment-specific-input-data" in experiment.paths:
        inputs.append("experiment-specific-input-data")
    if "supplied-totaled-sealevel-step-data" in experiment.paths:
        inputs.append("supplied-totaled-sealevel-step-data")

    # Outputs section (output-data-location)
    outputs = []
    if "output-data-location" in experiment.paths:
        outputs.append("output-data-location")

    # Module-specific sections (all keys that are module names)
    # Exclude top-level params, included_modules, inputs, outputs, and experiment_name
    excluded_keys = (
        set(experiment.top_level_params.keys())
        | set(experiment.fingerprint_params.keys())
        | set(included_modules)
        | set(inputs)
        | set(outputs)
        | {"experiment_name"}
    )
    module_keys = [
        key
        for key in module_sections.keys()
        if key not in excluded_keys and isinstance(module_sections[key], dict)
    ]

    # Sort module_keys so temperature_module appears first if it exists
    temperature_module_name = manifest.get("temperature_module")
    if (
        temperature_module_name
        and isinstance(temperature_module_name, str)
        and temperature_module_name.upper() != "NONE"
    ):
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

    env.globals["format_value"] = format_value
    env.globals["format_module"] = format_module_func
    # Also add as filter for alternative syntax
    env.filters["format_value"] = format_value

    # Create template
    template = env.from_string(YAML_TEMPLATE)

    # Render template
    try:
        rendered = template.render(
            experiment=experiment,
            manifest=manifest,
            module_sections=module_sections,
            included_modules=included_modules,
            inputs=inputs,
            outputs=outputs,
            module_keys=module_keys,
            module_registry_version=module_registry_version,
        )
    except Exception as e:
        raise ValueError(f"Error rendering Jinja2 template: {e}") from e

    # Write to file
    with open(output_path, "w") as f:
        f.write(rendered)
