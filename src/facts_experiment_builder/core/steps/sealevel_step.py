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
    def from_module_schemas(
        cls, schemas: List[ModuleSchema], climate_data_file: Optional[str] = None
    ) -> "SealevelStep":
        specs = []
        for schema in schemas:
            prefilled: Dict[str, str] = {}
            if climate_data_file and schema.uses_climate_file:
                output_vol_keys = schema.get_output_volume_input_keys()
                climate_keys = {k for k in output_vol_keys if "-" not in k} or {
                    "climate_data_file"
                }
                prefilled = {k: climate_data_file for k in climate_keys}
            specs.append(
                ModuleExperimentSpec.from_module_schema(
                    schema, prefilled_inputs=prefilled
                )
            )
        return cls(module_specs_list=specs)

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

    @property
    def module_names(self) -> List[str]:
        return [s.module_name for s in self.module_specs_list]
