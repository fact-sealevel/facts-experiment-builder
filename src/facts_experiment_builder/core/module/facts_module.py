"""In-memory representation of a module (analogous to *_module.yaml).

Does not contain everything needed to run a module; used to build
experiment-metadata content and, with experiment data, to build ModuleServiceSpec.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

@dataclass
class FactsModule:
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

