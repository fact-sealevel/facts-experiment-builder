from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.base import ExperimentStep


@dataclass
class ExtremeSealevelStep(ExperimentStep):
    module_spec: Optional[ModuleExperimentSpec] = None

    @classmethod
    def none_step(cls) -> "ExtremeSealevelStep":
        return cls(module_spec=None)

    @classmethod
    def from_module_schema(cls, schema: ModuleSchema) -> "ExtremeSealevelStep":
        return cls(module_spec=ModuleExperimentSpec.from_module_schema(schema))

    @classmethod
    def from_dict(
        cls, module_name: Optional[str], d: Dict[str, Any]
    ) -> "ExtremeSealevelStep":
        if not module_name:
            return cls.none_step()
        return cls(module_spec=ModuleExperimentSpec.from_dict(module_name, d))

    def is_configured(self) -> bool:
        return True if self.module_spec is None else self.module_spec.is_configured()

    def module_specs(self) -> List[ModuleExperimentSpec]:
        return [self.module_spec] if self.module_spec else []

    def to_dict(self) -> Dict[str, Any]:
        return self.module_spec.to_dict() if self.module_spec else {}

    def merge_defaults(
        self, defaults_yml: Dict[str, Any], schema: Optional[ModuleSchema] = None
    ) -> None:
        if self.module_spec is not None:
            self.module_spec.merge_defaults(defaults_yml, schema)

    @property
    def is_present(self) -> bool:
        return self.module_spec is not None

    @property
    def module_name(self) -> Optional[str]:
        return self.module_spec.module_name if self.module_spec else None
