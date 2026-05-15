from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.base import ExperimentStep
import logging

logger = logging.getLogger(__name__)


def _validate_regions(schema: ModuleSchema, regions: List[str]) -> None:
    """Raise ValueError if any region is not in the schema's allowed_values for 'region'."""
    allowed: Optional[List[str]] = None
    for opt_spec in schema.arguments.get("options", []):
        if opt_spec.get("name") == "region" and "allowed_values" in opt_spec:
            allowed = opt_spec["allowed_values"]
            break
    if allowed is None:
        return  # module has no allowed_values constraint; accept anything
    invalid = [r for r in regions if r not in allowed]
    if invalid:
        raise ValueError(
            f"Invalid region(s) {invalid} for module '{schema.module_name}'. "
            f"Allowed values: {allowed}"
        )


@dataclass
class SealevelStep(ExperimentStep):
    module_specs_list: List[ModuleExperimentSpec] = field(default_factory=list)
    supplied_totaled_sealevel_data: Optional[str] = None

    @classmethod
    def from_module_schemas(
        cls,
        schemas: List[ModuleSchema],
        climate_data_file: Optional[str] = None,
        module_regions: Optional[Dict[str, List[str]]] = None,
    ) -> "SealevelStep":
        """Build a SealevelStep from module schemas.

        Args:
            schemas: Module schemas for each sealevel module.
            climate_data_file: Pre-filled climate data file path, if known.
            module_regions: Optional dict mapping module names to a list of
                regions (e.g. {"emulandice2-glaciers": ["RGI01", "RGI02"]}).
                Modules listed here are expanded into one spec per region,
                named '<module>-<region>'.  Modules not in this dict produce
                a single spec as normal.
        """
        module_regions = module_regions or {}
        specs = []
        for schema in schemas:
            logger.info("Hydrating sealevel module: %s", schema.module_name)
            prefilled: Dict[str, str] = {}
            if climate_data_file and schema.uses_climate_file:
                output_vol_keys = schema.get_output_volume_input_keys()
                climate_keys = {k for k in output_vol_keys if "-" not in k} or {
                    "climate_data_file"
                }
                prefilled = {k: climate_data_file for k in climate_keys}

            regions = module_regions.get(schema.module_name)
            if regions:
                _validate_regions(schema, regions)
                for region in regions:
                    instance_name = f"{schema.module_name}-{region}"
                    logger.info("  Creating region instance: %s", instance_name)
                    specs.append(
                        ModuleExperimentSpec.from_module_schema(
                            schema,
                            prefilled_inputs=prefilled,
                            region=region,
                            instance_name=instance_name,
                        )
                    )
            else:
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
