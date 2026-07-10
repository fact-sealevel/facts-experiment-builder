from typing import Protocol
from facts_experiment_builder.core.module.module_schema import ModuleSchema


class ModuleDefinitionSource(Protocol):
    """Port where module definitions come from.
    application code depends on this class."""

    def get_schema(self, module_name: str) -> ModuleSchema: ...
    def module_names(self) -> frozenset[str]: ...
    def version(self) -> str: ...
