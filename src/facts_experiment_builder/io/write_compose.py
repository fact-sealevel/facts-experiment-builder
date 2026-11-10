"""Serialize and write the Docker Compose YAML file."""

from pathlib import Path

import yaml


def make_compose_yaml(
    content_dict: dict,
    sort_keys: bool = False,
    indent=3,  # 3 spaces for each level
    width=1000,  # Wide width to avoid line wrapping
    allow_unicode: bool = True,
) -> str:
    """Serialize a compose dict to a YAML string.

    Uses yaml.dump (not safe_dump), so values must be plain YAML types (dicts, lists,
    strings, numbers, bools) to get plain YAML out.

    Args:
        content_dict: Compose content, e.g. {"services": {...}} from generate_compose()
        sort_keys: Sort mapping keys. Default False keeps insertion order, so
            services appear in the order they were built.
        indent: Spaces per nesting level
        width: Maximum line width before PyYAML wraps a line; set wide so long
            command arguments and paths stay on one line
        allow_unicode: Write non-ASCII characters as-is instead of escaping them

    Returns:
        The YAML text.
    """
    yaml_content = yaml.dump(
        content_dict,
        sort_keys=sort_keys,
        indent=indent,
        width=width,
        allow_unicode=allow_unicode,
    )
    return yaml_content


def write_compose_yaml(
    compose_content: str,
    compose_path: Path,
) -> None:
    """Write Docker Compose YAML to file.

    Overwrites any existing file at compose_path.

    Args:
        compose_content: YAML text, from make_compose_yaml()
        compose_path: Where to write the file; its parent directory must exist
    """
    with open(compose_path, "w") as f:
        f.write(compose_content)
