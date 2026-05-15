from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)

from facts_experiment_builder.core.module.module_schema import ModuleSchema
import logging

logger = logging.getLogger(__name__)


def _resolve_filename(arg_spec: dict, options_context: Dict[str, Any]) -> Optional[str]:
    """Return filename for an arg spec, preferring filename_map over filename.

    filename_map structure:
        filename_map:
          <option-name>:
            <option-value>: <filename>

    Looks up the current option value in options_context.  Falls back to
    filename if the map is absent or the option value isn't in the map.
    """
    filename_map = arg_spec.get("filename_map")
    if filename_map and isinstance(filename_map, dict):
        for option_name, value_map in filename_map.items():
            if not isinstance(value_map, dict):
                continue
            option_value = options_context.get(option_name) or options_context.get(
                option_name.replace("-", "_")
            )
            if option_value is not None and option_value in value_map:
                return value_map[option_value]
    return arg_spec.get("filename")


def _options_defaults_from_schema(module_schema: ModuleSchema) -> Dict[str, Any]:
    """Extract {option-name: default_value} from the schema's options specs.

    Both kebab-case and snake_case keys are included so filename_map lookups
    work regardless of which form appears in the map.
    """
    context: Dict[str, Any] = {}
    for opt_spec in module_schema.arguments.get("options", []):
        name = opt_spec.get("name", "")
        if name and "default_value" in opt_spec:
            context[name] = opt_spec["default_value"]
            context[name.replace("-", "_")] = opt_spec["default_value"]
    return context


def _build_section_from_fields(
    fields: list[dict],
    include_filename: bool = False,
    prefilled_values: Optional[Dict[str, str]] = None,
    options_context: Optional[Dict[str, Any]] = None,
) -> Dict:
    prefilled_values = prefilled_values or {}
    options_context = options_context or {}
    result = {}

    for field_spec in fields:
        source = field_spec.get("source", "")
        logger.info(f"Processing field: {field_spec.get('name', 'unknown')}")
        if "." not in source:
            continue
        # Pull out the last part of this obj
        underscore_name = source.split(".")[-1]
        clue = field_spec.get("help", f"Add your {underscore_name} here.")
        bundle = create_metadata_bundle(clue, prefilled_values.get(underscore_name))
        default_value = field_spec.get("default_value")
        if default_value:
            bundle["default_value"] = default_value
            logger.info("...default: %s", default_value)

        if include_filename:
            filename = _resolve_filename(field_spec, options_context)
            if filename:
                bundle["filename"] = filename
            logger.info("...filename: %s", filename)
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
    base_module_name: Optional[str] = None  # set when module_name is a region instance

    # Constructors
    @classmethod
    def from_module_schema(
        cls,
        module_schema: ModuleSchema,
        prefilled_inputs: Optional[Dict[str, str]] = None,
        region: Optional[str] = None,
        instance_name: Optional[str] = None,
    ) -> "ModuleExperimentSpec":
        """Build an initial spec with clue,value,default,filename placeholders.

        Args:
            module_schema: The base module schema.
            prefilled_inputs: Input values to pre-fill (e.g. climate_data_file).
            region: When set, resolves filename_map entries and pre-sets the
                region option as a plain value (not a clue/value bundle).
            instance_name: Service/spec name to use instead of module_schema.module_name
                (e.g. 'emulandice2-glaciers-RGI01'). Required when region is set.
        """
        prefilled_inputs = prefilled_inputs or {}
        effective_name = instance_name or module_schema.module_name

        logger.info("Building module experiment spec for: %s", effective_name)

        # Build options context for filename_map resolution.
        # If a specific region was supplied, it takes precedence over the schema default.
        options_context = _options_defaults_from_schema(module_schema)
        if region:
            options_context["region"] = region

        module_inputs = _build_section_from_fields(
            module_schema.arguments.get("inputs", []),
            include_filename=True,
            prefilled_values=prefilled_inputs,
            options_context=options_context,
        )

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
        # When a region is specified, overwrite the region bundle with a plain value
        # so the experiment-config renders 'region: RGI01' instead of a clue/placeholder.
        if region and "region" in options:
            options["region"] = region

        fingerprint_params = _build_section_from_fields(
            module_schema.arguments.get("fingerprint_params", []),
            include_filename=True,
            options_context=options_context,
        )

        module_outputs: Dict[str, Any] = {}
        for arg_spec in module_schema.get_file_outputs():
            arg_name = arg_spec.get("name", "")
            if not arg_name:
                continue
            filename = _resolve_filename(arg_spec, options_context)
            if not filename:
                raise ValueError(
                    f"Module {module_schema.module_name} output '{arg_name}' is missing "
                    "a 'filename' or 'filename_map' key in module YAML (arguments.outputs)."
                )
            output_type = arg_spec.get("output_type", "")
            if not output_type:
                raise ValueError(
                    f"Module {module_schema.module_name} output '{arg_name}' is missing "
                    "required 'output_type' key in module YAML (arguments.outputs)."
                )
            module_outputs[arg_name] = {
                "value": f"{effective_name}/{filename}",
                "output_type": output_type,
            }
        for arg_spec in module_schema.get_other_outputs():
            arg_name = arg_spec.get("name", "")
            if not arg_name:
                continue
            module_outputs[arg_name] = {"value": effective_name}

        return cls(
            module_name=effective_name,
            inputs=module_inputs,
            options=options,
            outputs=module_outputs,
            fingerprint_params=fingerprint_params,
            image=module_schema.container_image,
            base_module_name=module_schema.module_name if instance_name else None,
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
            base_module_name=d.get("_base_module") or None,
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
        if self.base_module_name:
            d["_base_module"] = self.base_module_name
        return d
