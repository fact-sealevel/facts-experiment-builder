from pathlib import Path
from facts_experiment_builder.core.components.metadata_bundle import is_metadata_value
from facts_experiment_builder.core.experiment.experiment_config import (
    ExperimentConfig,
)
from typing import Any, List, Dict
from jinja2 import Environment, PackageLoader, StrictUndefined

from markupsafe import Markup


def format_module_value(key: str, value: Any, indent: int = 2) -> List[str]:
    """Format a single key-value pair in a module section, handling clue/value dicts.

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
            if isinstance(filename, list):
                for f in filename:
                    if isinstance(f, str) and ("/" in f or " " in f):
                        lines.append(
                            f'{indent_str}  - "{f}"  # filename from module defaults'
                        )
                    else:
                        lines.append(
                            f"{indent_str}  - {f}  # filename from module defaults"
                        )
            elif isinstance(filename, str) and ("/" in filename or " " in filename):
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
        if not value:
            lines.append(f"{indent_str}{key}: {{}}")
            return lines
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
    """Format a module section with comment handling and clue/value support.

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
    """Format a simple YAML value (not a metadata value dict).

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
    """Format a YAML value with clue/value dict structure.

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


def write_config_jinja2(experiment_config: ExperimentConfig, config_path: Path):
    # Add custom functions and filters
    def format_value(value):
        result = format_yaml_value(value)
        # Return as Markup to prevent Jinja2 from escaping
        return Markup(result)

    def format_module_func(key, data):
        result = format_module(key, data)
        return Markup(result)

    # create jinja2 env
    env = Environment(
        loader=PackageLoader("facts_experiment_builder", "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.globals["format_value"] = format_value
    env.globals["format_module"] = format_module_func
    # Also add as filter for alternative syntax
    env.filters["format_value"] = format_value

    # Create template
    template = env.get_template("experiment-config.yaml.j2")

    # Render template
    try:
        rendered = template.render(**vars(experiment_config))
    except Exception as e:
        raise ValueError(f"Error rendering Jinja2 template: {e}") from e

    # Write to file
    with open(config_path, "w") as f:
        f.write(rendered)
