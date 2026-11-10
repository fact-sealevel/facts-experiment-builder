"""Build Docker Compose service dicts from backend-neutral ServiceRun objects."""

from collections.abc import Iterable
from typing import Any

from facts_experiment_builder.core.module.service_run import (
    ServiceDependency,
    ServiceRun,
)

_DEFAULT_CONDITION = "service_completed_successfully"


def to_compose_service(
    run: ServiceRun, depends_on: Iterable[ServiceDependency] = ()
) -> dict[str, Any]:
    """Build the Docker Compose service dict for one ServiceRun.

    Args:
        run: Backend-neutral service, from ModuleServiceSpec.to_service_run().
        depends_on: Services that must complete first. A name listed more than once
            keeps its first position and its last condition.
    """
    return build_compose_service_dict(
        image_str=f"{run.image.image_url}:{run.image.image_tag}",
        command=run.args,
        volumes=run.binds,
        depends_on={
            dep.service: {"condition": dep.condition or _DEFAULT_CONDITION}
            for dep in depends_on
        },
        environment=run.env,
    )


def build_compose_service_dict(
    image_str: str,
    command: list[str],
    volumes: list[str],
    depends_on: dict[str, Any] | None = None,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a Docker Compose service dictionary.

    Args:
        image_str: Full image string (e.g. "repo/image:tag")
        command: List of command-line argument strings (e.g. ["--pipeline-id=aaa", ...])
        volumes: List of volume mount strings (e.g. ["/host/path:/container/path"])
        depends_on: Optional dict mapping service names to dependency conditions
        environment: Optional dict of environment variables to set in the container

    Returns:
        Dictionary suitable for a single service in a compose file (image, command, volumes, depends_on, restart)
    """
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
