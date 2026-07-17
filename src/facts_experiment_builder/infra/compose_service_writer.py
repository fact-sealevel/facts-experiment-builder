"""Build Docker Compose service dict from resolved service pieces (image, command, volumes, depends_on)."""

from typing import Dict, Any, List, Optional


def build_compose_service_dict(
    image_str: str,
    command: List[str],
    volumes: List[str],
    depends_on: Optional[Dict[str, Any]] = None,
    environment: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build a Docker Compose service dictionary from a ModuleServiceSpec.

    Args:
        image_str: Full image string (e.g. "repo/image:tag")
        command: List of command-line argument strings (e.g. ["--pipeline-id=aaa", ...])
        volumes: List of volume mount strings (e.g. ["/host/path:/container/path"])
        depends_on: Optional dict mapping service names to dependency conditions
        environment: Optional dict of environment variables to set in the container

    Returns:
        Dictionary suitable for a single service in a compose file (image, command, volumes, depends_on, restart)
    """
    # TODO: better fix for this but should work for now
    if command and command[0] == "main":
        command = command[1:]
    service = {
        "image": image_str,
        "command": command,
        "volumes": volumes,
        "restart": "no",
    }
    if environment:
        service["environment"] = environment
    if depends_on:
        service["depends_on"] = depends_on
    return service
