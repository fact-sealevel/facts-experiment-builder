import yaml
from typing import Dict
from pathlib import Path


def make_compose_yaml(
    content_dict: Dict,
    sort_keys: bool = False,
    indent=3,  # 3 spaces for each level
    width=1000,  # Wide width to avoid line wrapping
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


def write_compose_yaml(
    compose_content: str,
    compose_path: Path,
) -> None:
    """Write Docker Compose YAML to file."""
    with open(compose_path, "w") as f:
        f.write(compose_content)
