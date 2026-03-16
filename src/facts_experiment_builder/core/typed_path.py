"""Typed path values: host or container. Used so the command builder can apply a single rule (container pass-through, host rewrite)."""

from dataclasses import dataclass
from typing import List, Literal, Union

PathKind = Literal["host", "container"]


@dataclass(frozen=True)
class TypedPath:
    """A path with an explicit host or container kind."""

    path: str
    kind: PathKind

    def __str__(self) -> str:
        return self.path


def HostPath(path: str) -> TypedPath:
    """Path on the host filesystem; builder will rewrite to container path."""
    return TypedPath(path=path, kind="host")


def ContainerPath(path: str) -> TypedPath:
    """Path inside the container; builder uses as-is."""
    return TypedPath(path=path, kind="container")


PathValue = Union[TypedPath, List[TypedPath]]
