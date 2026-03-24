"""In-memory representation of a module schema (analogous to *_module.yaml).

Does not contain everything needed to run a module; used to build
experiment-metadata content and, with experiment data, to build ModuleServiceSpec.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# TODO this would need to change if the module schema yaml structure changes.
# is that fine or do we want it to be more flexibly defined?


@dataclass(frozen=True)
class ModuleDefaultValues:
    """Default values for a module."""

    inputs: Dict[str, Any]
    options: Dict[str, Any]
    outputs: Dict[str, Any]


@dataclass
class ModuleSchema:
    """In-memory representation of a module YAML file (*_module.yaml)."""

    module_name: str
    container_image: str
    arguments: Dict[str, List[Dict[str, Any]]]  # top_level, options, inputs, outputs
    volumes: Dict[str, Dict[str, Any]]
    depends_on: Optional[List[Dict[str, Any]]] = None
    command: str = ""
    uses_climate_file: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.arguments is None:
            self.arguments = {}
        if self.volumes is None:
            self.volumes = {}


@dataclass(frozen=True)
class ScenarioConfig:
    """Scenario configuration details."""

    scenario_name: str
    description: str


@dataclass(frozen=True)
class ModuleContainerImage:
    """Container image for a module."""

    image_url: str
    image_tag: str
