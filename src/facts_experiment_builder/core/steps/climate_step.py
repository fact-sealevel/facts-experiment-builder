from dataclasses import dataclass
from typing import Optional, Dict, List

from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.base import ExperimentStep


@dataclass
class ClimateStep(ExperimentStep):
    module_spec: Optional[ModuleExperimentSpec] = None
    alternate_climate_data: Optional[str] = None  # used when no climate module passed
    _not_needed: bool = False  # used when totaled sealevel data bypasses this step

    @classmethod
    def from_module_schema(cls, schema: ModuleSchema) -> "ClimateStep":
        return cls(module_spec=ModuleExperimentSpec.from_module_schema(schema))

    @classmethod
    def from_dict(cls, module_name: Optional[str], d: Dict) -> "ClimateStep":
        if not module_name or module_name.upper() == "NONE":
            return cls(alternate_climate_data=d.get("alternate_climate_data"))
        return cls(module_spec=ModuleExperimentSpec.from_dict(module_name, d))

    @classmethod
    def not_needed(cls) -> "ClimateStep":
        """Use when totaled sealevel data is provided and no climate step is required."""
        return cls(module_spec=None, alternate_climate_data=None, _not_needed=True)

    def is_configured(self) -> bool:
        if self._not_needed:
            return True
        if self.module_spec is not None:
            return self.module_spec.is_configured()
        return self.alternate_climate_data is not None

    def module_specs(self) -> List[ModuleExperimentSpec]:
        return [self.module_spec] if self.module_spec else []

    def merge_defaults(self, defaults_yml, module_schema=None) -> None:
        if self.module_spec is not None:
            self.module_spec.merge_defaults(defaults_yml, module_schema)

    def to_dict(self) -> dict:
        return self.module_spec.to_dict() if self.module_spec else {}

    @property
    def is_present(self) -> bool:
        return self.module_spec is not None

    @property
    def module_name(self) -> Optional[str]:
        return self.module_spec.module_name if self.module_spec else None
