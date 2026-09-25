from dataclasses import dataclass, field
from typing import Any

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.base import ExperimentStep


@dataclass
class SealevelStep(ExperimentStep):
    module_specs_list: list[ModuleExperimentSpec] = field(default_factory=list)
    supplied_totaled_sealevel_data: str | None = None

    @classmethod
    def from_module_schemas(
        cls,
        schemas: list[ModuleSchema],
        climate_files: dict[str, str] | None = None,
        module_regions: dict[str, list[str]] | None = None,
        top_level_context: dict[str, Any] | None = None,
    ) -> "SealevelStep":
        """Build a SealevelStep from module schemas.

        Args:
            schemas: Module schemas for each sealevel module.
            climate_files: Per-module climate file paths, keyed by module name.
                Each value is the relative path (e.g. "fair-temperature/climate.nc")
                to pre-fill into that module's climate input.
            module_regions: Optional dict mapping module names to a list of
                region values (e.g. {"emulandice2-glaciers": ["RGI01", "RGI02"]}).
                When provided, pre-fills the region option for that module so the
                experiment-config renders a list value that generates multiple
                ``--region`` flags in the compose command.
            top_level_context: Top-level experiment params (e.g. {"pyear_end": 2300})
                passed through to ModuleExperimentSpec for multi-key filename_map
                resolution.
        """
        climate_files = climate_files or {}
        module_regions = module_regions or {}
        specs = []
        for schema in schemas:
            prefilled: dict[str, str] = {}
            climate_data_file = climate_files.get(schema.module_name)
            if climate_data_file and schema.uses_climate_file:
                climate_keys = schema.get_output_volume_input_keys() or {
                    "climate-data-file"
                }
                prefilled = {k: climate_data_file for k in climate_keys}

            regions = module_regions.get(schema.module_name)
            prefilled_options = {"region": regions} if regions else None
            specs.append(
                ModuleExperimentSpec.from_module_schema(
                    schema,
                    prefilled_inputs=prefilled,
                    prefilled_options=prefilled_options,
                    top_level_context=top_level_context,
                )
            )
        return cls(module_specs_list=specs)

    @classmethod
    def from_dict(
        cls, module_names: list[str], metadata: dict[str, Any]
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

    def module_specs(self) -> list[ModuleExperimentSpec]:
        return list(self.module_specs_list)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Returns {module_name: spec_dict, ...} for each sealevel module."""
        return {s.module_name: s.to_dict() for s in self.module_specs_list}

    @property
    def module_names(self) -> list[str]:
        return [s.module_name for s in self.module_specs_list]
