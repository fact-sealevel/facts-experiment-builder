from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)

from facts_experiment_builder.core.module.module_schema import ModuleSchema
import logging

logger = logging.getLogger(__name__)


def _build_section_from_fields(
    fields: list[dict],
    include_filename: bool = False,
    prefilled_values: Optional[Dict[str, str]] = None,
) -> Dict:
    prefilled_values = prefilled_values or {}
    result = {}

    for field_spec in fields:
        source = field_spec.get("source", "")
        if "." not in source:
            continue
        # Pull out the last part of this obj
        underscore_name = source.split(".")[-1]
        clue = field_spec.get("help", f"Add your {underscore_name} here.")
        bundle = create_metadata_bundle(clue, prefilled_values.get(underscore_name))
        default_value = field_spec.get("default_value")
        if default_value:
            bundle["default_value"] = default_value
            logger.info("default: %s", default_value)

        if include_filename:
            filename = field_spec.get("filename")
            if filename:
                bundle["filename"] = filename
            logger.info("filename: %s", filename)
        result[underscore_name] = bundle

    return result


@dataclass
class ModuleExperimentSpec:
    """
    In-memory representation of one module's section in experiment-config.yaml.
    Fields mirror the dict shape used in the YAML:
        inputs:  {field_name: clue/value-bundle-or-plain-value}
        options: {field_name: clue/value-bundle-or-plain-value}
        fingerprint-params: ...
        outputs: {output_name: {"value": path, "output_type": ...}}
        image:   str (container image URL)
    """

    module_name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    fingerprint_params: Dict[str, Any] = field(default_factory=dict)
    image: str = ""

    # Constructors
    @classmethod
    def from_module_schema(
        cls,
        module_schema: ModuleSchema,
        prefilled_inputs: Optional[Dict[str, str]] = None,
    ) -> "ModuleExperimentSpec":
        """Build an initial spec with clue,value,default,filename placeholders for each field in each section from a moduleschema"""
        prefilled_inputs = prefilled_inputs or {}

        # inputs
        logger.info(
            "Building module experiment spec for module: %s", module_schema.module_name
        )

        module_inputs = _build_section_from_fields(
            module_schema.arguments.get("inputs", []),
            include_filename=True,
            prefilled_values=prefilled_inputs,
        )
        # new stuff:
        options: Dict[str, Any] = {}
        top_level_names = [
            arg.get("name", "") for arg in module_schema.arguments.get("top_level", [])
        ]
        if top_level_names:
            options[
                f"# Options inherited from top-level metadata: {', '.join(top_level_names)}"
            ] = None
        options.update(
            _build_section_from_fields(module_schema.arguments.get("options", []))
        )

        fingerprint_params = _build_section_from_fields(
            module_schema.arguments.get("fingerprint_params", []), include_filename=True
        )

        module_outputs: Dict[str, Any] = {}
        for arg_spec in module_schema.get_file_outputs():
            arg_name = arg_spec.get("name", "")
            if not arg_name:
                continue
            filename = arg_spec.get("filename")
            if not filename:
                raise ValueError(
                    f"Module {module_schema.module_name} output '{arg_name}' is missing "
                    "required 'filename' key in module YAML (spec. in arguments.outputs)."
                )
            output_type = arg_spec.get("output_type", "")
            if not output_type:
                raise ValueError(
                    f"Module {module_schema.module_name} output '{arg_name}' is missing "
                    "required 'output_type' key in module YAML (arguments.outputs)."
                )
            module_outputs[arg_name] = {
                "value": f"{module_schema.module_name}/{filename}",
                "output_type": output_type,
            }
        for arg_spec in module_schema.get_other_outputs():
            arg_name = arg_spec.get("name", "")
            if not arg_name:
                continue
            module_outputs[arg_name] = {"value": module_schema.module_name}

        return cls(
            module_name=module_schema.module_name,
            inputs=module_inputs,
            options=options,
            outputs=module_outputs,
            fingerprint_params=fingerprint_params,
            image=module_schema.container_image,
        )

    @classmethod
    def from_dict(cls, module_name: str, d: Dict[str, Any]) -> "ModuleExperimentSpec":
        return cls(
            module_name=module_name,
            inputs=dict(d.get("inputs") or {}),
            options=dict(d.get("options") or {}),
            outputs=dict(d.get("outputs") or {}),
            fingerprint_params=dict(d.get("fingerprint_params") or {}),
            image=d.get("image", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize back to raw dict used in experiment-config.yaml"""
        d: Dict[str, Any] = {
            "inputs": dict(self.inputs),
            "options": dict(self.options),
            "image": self.image,
            "outputs": dict(self.outputs),
        }
        if self.fingerprint_params:
            d["fingerprint_params"] = dict(self.fingerprint_params)
        return d
