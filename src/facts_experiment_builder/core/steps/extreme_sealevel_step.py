from dataclasses import dataclass
from typing import Any

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.base import ExperimentStep


@dataclass
class ExtremeSealevelStep(ExperimentStep):
    module_spec: ModuleExperimentSpec | None = None

    @classmethod
    def from_module_schema(cls, schema: ModuleSchema) -> "ExtremeSealevelStep":
        return cls(module_spec=ModuleExperimentSpec.from_module_schema(schema))

    @classmethod
    def from_dict(
        cls, module_name: str | None, d: dict[str, Any]
    ) -> "ExtremeSealevelStep":
        if not module_name:
            return cls()
        return cls(module_spec=ModuleExperimentSpec.from_dict(module_name, d))

    def is_configured(self) -> bool:
        return True if self.module_spec is None else self.module_spec.is_configured()

    def module_specs(self) -> list[ModuleExperimentSpec]:
        return [self.module_spec] if self.module_spec else []

    def to_dict(self) -> dict[str, Any]:
        return self.module_spec.to_dict() if self.module_spec else {}

    def merge_defaults(
        self, defaults_yml: dict[str, Any], schema: ModuleSchema | None = None
    ) -> None:
        if self.module_spec is not None:
            self.module_spec.merge_defaults(defaults_yml, schema)

    @property
    def is_present(self) -> bool:
        return self.module_spec is not None

    @property
    def module_name(self) -> str | None:
        return self.module_spec.module_name if self.module_spec else None
