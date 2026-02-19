"""Build Docker Compose service dict from resolved service pieces (image, command, volumes, depends_on)."""

from typing import Dict, Any, List, Optional


def build_service_dict(
    image_str: str,
    command: List[str],
    volumes: List[str],
    depends_on: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a Docker Compose service dictionary from resolved pieces.

    Args:
        image_str: Full image string (e.g. "repo/image:tag")
        command: List of command-line argument strings (e.g. ["--pipeline-id=aaa", ...])
        volumes: List of volume mount strings (e.g. ["/host/path:/container/path"])
        depends_on: Optional dict mapping service names to dependency conditions

    Returns:
        Dictionary suitable for a single service in a compose file (image, command, volumes, depends_on, restart)
    """
    service = {
        "image": image_str,
        "command": command,
        "volumes": volumes,
        "restart": "no",
    }
    if depends_on:
        service["depends_on"] = depends_on
    return service
