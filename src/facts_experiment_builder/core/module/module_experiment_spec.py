from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
    is_metadata_value,
)

from facts_experiment_builder.core.module.module_schema import ModuleSchema
import logging

logger = logging.getLogger(__name__)


def get_clue_from_module_yaml(
    module_schema: ModuleSchema, arg_type: str, field_name: str
):
    """Extract help text from module schema for a specific field."""
    arg_specs = module_schema.arguments.get(arg_type, [])
    for arg_spec in arg_specs:
        source = arg_spec.get("source", "")
        if "." in source and source.split(".")[-1] == field_name:
            help_text = arg_spec.get("help", "")
            if help_text:
                return help_text
    return f"add your {field_name} here"

def get_default_value_from_module_yaml(
    module_schema: ModuleSchema,
    arg_type: str,
    field_name:str
):
    """Extract default value from module schema for a given field."""
    # This is a list of dicts of the field for each arg_type (inputs,options...)
    # keys are name, type, source, help, default value.
    arg_specs = module_schema.arguments.get(arg_type, [])

    for arg_spec in arg_specs:
        source = arg_spec.get("source","")

        if "." in source and source.split(".")[-1] == field_name:
            default_value = arg_spec.get("default_value", "")

            if default_value:
                return default_value
    return f"no default value for {field_name}"

def get_filename_from_module_yaml(
    module_schema: ModuleSchema,
    arg_type: str,
    field_name:str
):
    """Extract filename from module schema for a given field."""
    arg_specs = module_schema.arguments.get(arg_type, [])
    for arg_spec in arg_specs:
        source = arg_spec.get("source","")
        filename = arg_spec.get('filename','')
        #if "." in source and source.split(".")[-1] == field_name:
        #    filename = arg_spec.get("filename", "")
        #    print('filename: ', filename)
        if filename:
            return filename
    return f"no specified filename for {field_name}"

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
    def from_module_schema(cls, module_schema: ModuleSchema) -> "ModuleExperimentSpec":
        """Build an initial spec with clue,value,default,filename placeholders from a moduleschema"""
        # inputs
        module_inputs: Dict[str, Any] = {}

        for arg_spec in module_schema.arguments["inputs"]:
            source = arg_spec.get("source", "")
            if "." not in source:
                continue
            snake_field_name = source.split(".")[-1]
            kebab_field_name = snake_field_name.replace("_", "-")
            logger.info("snake %s", snake_field_name)

            #Extract clue text from module yaml
            clue = get_clue_from_module_yaml(
                module_schema=module_schema,
                arg_type="inputs",
                field_name=kebab_field_name,
            )
            # Extract any specified filenames
            filename = get_filename_from_module_yaml(
                module_schema= module_schema,
                arg_type = "inputs",
                field_name = kebab_field_name
            )
            module_inputs[snake_field_name] = {
                'clue': clue,
                'filename': filename
            }
            #create_metadata_bundle(clue = clue)

        # options
        module_options: Dict[str, Any] = {}
        top_level_args = module_schema.arguments.get("top_level", [])
        top_level_names = [arg.get("name", "") for arg in top_level_args]
        if top_level_names:
            module_options[
                f"# Options inherited from top-level metadata: {', '.join(top_level_names)}"
            ] = None
        for arg_spec in module_schema.arguments.get("options", []):
            source = arg_spec.get("source", "")
            if "." not in source:
                continue
            snake_field_name = source.split(".")[-1]
            clue = get_clue_from_module_yaml(
                module_schema=module_schema,
                arg_type="options",
                field_name=snake_field_name,
            )
            default_value = get_default_value_from_module_yaml(
                module_schema = module_schema,
                arg_type="options",
                field_name = snake_field_name
            )
            module_options[snake_field_name] = {
                'clue': clue,
                'default_value': default_value
            }
            #module_options[snake_field_name] = create_metadata_bundle(clue)

        # fingerprint_params (module-specific only — entries sourced from module_inputs.fingerprint_params.*)
        module_fingerprint_params: Dict[str, Any] = {}
        for arg_spec in module_schema.arguments.get("fingerprint_params", []):
            source = arg_spec.get("source", "")
            if not source.startswith("module_inputs.fingerprint_params."):
                continue
            snake_field_name = source.split(".")[-1]
            clue = get_clue_from_module_yaml(
                module_schema=module_schema,
                arg_type="fingerprint_params",
                field_name=snake_field_name,
            )
            default_value = get_default_value_from_module_yaml(
                module_schema = module_schema,
                arg_type="fingerprint_params",
                field_name = snake_field_name
            )
            module_options[snake_field_name] = {
                'clue': clue,
                'default_value': default_value
            }
            module_fingerprint_params[snake_field_name] = {
                'clue': clue,
                'default_value': default_value
            }
            #clue = arg_spec.get("help", f"add your {snake_field_name} here")
            #module_fingerprint_params[snake_field_name] = create_metadata_bundle(clue)

        # outputs
        module_outputs: Dict[str, Any] = {}
        for arg_spec in module_schema.get_file_outputs():
            arg_name = arg_spec.get("name", "")
            if not arg_name:
                continue
            filename = arg_spec.get("filename")
            if not filename:
                raise ValueError(
                    f"Module {module_schema.module_name} output '{arg_name}' is missing"
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
            options=module_options,
            outputs=module_outputs,
            fingerprint_params=module_fingerprint_params,
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

    ##
    # Serialization

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

    # Mutation
    def merge_defaults(
        self,
        defaults_yml: Dict[str, Any],
        module_schema: Optional[ModuleSchema] = None,
    ) -> None:
        """Merge a module's defaults YAML into this spec in place."""
        if not defaults_yml:
            return

        section_map = {
            "inputs": self.inputs,
            "options": self.options,
            "fingerprint_params": self.fingerprint_params,
        }

        for section_key, section_defaults in defaults_yml.items():
            if section_key == "image":
                if isinstance(section_defaults, dict):
                    image_url = section_defaults.get("image_url")
                    if image_url:
                        self.image = image_url
                continue

            if section_key not in section_map:
                continue

            current_section = section_map[section_key]
            if not (
                isinstance(section_defaults, dict) and isinstance(current_section, dict)
            ):
                continue

            comment_keys = {
                k: v
                for k, v in current_section.items()
                if isinstance(k, str) and k.startswith("#")
            }

            for nested_key, nested_default in section_defaults.items():
                matching_key = self._find_matching_key(current_section, nested_key)

                if matching_key is not None:
                    nested_current = current_section[matching_key]
                    if is_metadata_value(nested_current):
                        nested_current["value"] = nested_default
                    elif nested_current is None or nested_current == "":
                        clue = self._get_clue(module_schema, section_key, matching_key)
                        current_section[matching_key] = create_metadata_bundle(
                            clue or f"add your {matching_key} here", nested_default
                        )
                    else:
                        current_section[matching_key] = create_metadata_bundle(
                            f"add you {matching_key} here", nested_default
                        )
                else:
                    snake_key = nested_key.replace("-", "_")
                    kebab_key = (
                        nested_key.replace("_", "-")
                        if "_" in nested_key
                        else nested_key
                    )
                    if snake_key in current_section:
                        nc = current_section[snake_key]
                        if is_metadata_value(nc):
                            nc["value"] = nested_default
                        else:
                            current_section[snake_key] = create_metadata_bundle(
                                f"add your {snake_key} here", nested_default
                            )
                    elif kebab_key in current_section and kebab_key != nested_key:
                        nc = current_section[kebab_key]
                        if is_metadata_value(nc):
                            nc["value"] = nested_default
                        else:
                            current_section[kebab_key] = create_metadata_bundle(
                                f"add your {kebab_key} here", nested_default
                            )
                    else:
                        clue = self._get_clue(module_schema, section_key, snake_key)
                        if not clue:
                            clue = self._get_clue(
                                module_schema, section_key, nested_key
                            )
                        current_section[snake_key] = create_metadata_bundle(
                            clue or f"add your {snake_key} here", nested_default
                        )
            for ck, cv in comment_keys.items():
                if ck not in current_section:
                    current_section[ck] = cv

    ##
    # query
    def is_configured(self) -> bool:
        """Return True if this spec has no unfilled clue/value bundles (value=None)."""

        def _any_unfilled(obj: Any) -> bool:
            if isinstance(obj, dict):
                if "clue" in obj:
                    return obj.get("value") is None
                return any(_any_unfilled(v) for v in obj.values())
            return False

        return not _any_unfilled(self.to_dict())

    # private helpers
    @staticmethod
    def _find_matching_key(
        current_section: Dict[str, Any],
        nested_key: str,
    ) -> Optional[str]:
        if nested_key in current_section:
            return nested_key
        snake = nested_key.replace("-", "_")
        if snake in current_section:
            return snake
        kebab = nested_key.replace("_", "-")
        if kebab in current_section:
            return kebab
        return None

    @staticmethod
    def _get_clue(
        module_schema: Optional[ModuleSchema], section_key: str, field_name: str
    ) -> str:
        if module_schema and section_key in ("inputs", "options"):
            return get_clue_from_module_yaml(
                module_schema=module_schema,
                arg_type=section_key,
                field_name=field_name,
            )
        return ""
