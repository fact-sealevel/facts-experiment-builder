import yaml
from typing import Dict
from pathlib import Path

def make_compose_yaml(
    content_dict: Dict,
    sort_keys: bool = False,
    indent=3, #3 spaces for each level
    width=1000, #Wide width to avoid line wrapping
    allow_unicode: bool = True,
    ) -> str:

    yaml_content = yaml.dump(
        content_dict,
        sort_keys=sort_keys,
        indent=indent,
        width=width,
        allow_unicode=allow_unicode,
    )
    return yaml_content

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

def write_compose_yaml(
    compose_content: str,
    output_path: Path,
) -> None:
    """Write Docker Compose YAML to file."""
    with open(output_path, "w") as f:
        f.write(compose_content)