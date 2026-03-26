"""Typed path values: host or container. Used so the command builder can apply a single rule (container pass-through, host rewrite)."""

from dataclasses import dataclass
from typing import List, Literal, Union

PathKind = Literal["host", "container", "experiment_specific_in"]


@dataclass(frozen=True)
class TypedPath:
    """A path with an explicit routing kind.

    Kinds:
    - "host": host path routed to a standard module input volume; container destination
      determined by the module YAML mount spec.
    - "container": already a container path; used as-is.
    - "experiment_specific_in": host path for user-supplied experiment data (e.g.
      climate data passed via --climate-step-data); always routed to
      /mnt/experiment_specific_in/<filename> with the parent directory volume-mounted.
    """

    path: str
    kind: PathKind

    def __str__(self) -> str:
        return self.path


def HostPath(path: str) -> TypedPath:
    """Path on the host filesystem; builder will rewrite to container path via module YAML mount spec."""
    return TypedPath(path=path, kind="host")


def ContainerPath(path: str) -> TypedPath:
    """Path inside the container; builder uses as-is."""
    return TypedPath(path=path, kind="container")


def ExperimentSpecificInputPath(path: str) -> TypedPath:
    """Host path to a user-supplied experiment data file.

    Builder routes to /mnt/experiment_specific_in/<filename> and adds
    a volume mount for the file's parent directory.
    """
    return TypedPath(path=path, kind="experiment_specific_in")


PathValue = Union[TypedPath, List[TypedPath]]
