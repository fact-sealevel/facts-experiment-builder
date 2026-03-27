from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.base import ExperimentStep


@dataclass
class SealevelStep(ExperimentStep):
    module_specs_list: List[ModuleExperimentSpec] = field(default_factory=list)
    supplied_totaled_sealevel_data: Optional[str] = None

    @classmethod
    def from_module_schemas(cls, schemas: List[ModuleSchema]) -> "SealevelStep":
        return cls(
            module_specs_list=[
                ModuleExperimentSpec.from_module_schema(s) for s in schemas
            ]
        )

    @classmethod
    def from_dict(
        cls, module_names: List[str], metadata: Dict[str, Any]
    ) -> "SealevelStep":
        specs = [
            ModuleExperimentSpec.from_dict(name, metadata.get(name) or {})
            for name in module_names
        ]
        return cls(module_specs_list=specs)

    def is_configured(self) -> bool:
        if self.supplied_totaled_sealevel_data is not None:
            return True
        return all(s.is_configured() for s in self.module_specs_list)

    def module_specs(self) -> List[ModuleExperimentSpec]:
        return list(self.module_specs_list)

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Returns {module_name: spec_dict, ...} for each sealevel module."""
        return {s.module_name: s.to_dict() for s in self.module_specs_list}

    def merge_defaults_for_module(
        self,
        module_name: str,
        defaults_yml: Dict[str, Any],
        schema: Optional[ModuleSchema] = None,
    ) -> None:
        for spec in self.module_specs_list:
            if spec.module_name == module_name:
                spec.merge_defaults(defaults_yml, schema)
                return

    @property
    def module_names(self) -> List[str]:
        return [s.module_name for s in self.module_specs_list]
