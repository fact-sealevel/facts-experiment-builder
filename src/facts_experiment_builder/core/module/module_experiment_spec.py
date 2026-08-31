from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema

logger = logging.getLogger(__name__)


def _map_get(mapping: Dict[str, Any], val: Any) -> Any:
    """Look up val in mapping, tolerating int vs.

    string key mismatches.     YAML parses bare integers as int, but a value coming from
    the CLI may be a     string.  Try val as-is, then str(val), then int(val) for
    numeric strings.
    """
    result = mapping.get(val)
    if result is None:
        result = mapping.get(str(val))
    if result is None and isinstance(val, str) and val.lstrip("-").isdigit():
        try:
            result = mapping.get(int(val))
        except (ValueError, TypeError):
            pass
    return result


def _multi_key_miss(arg_spec: dict, key: str, val: Any, parent: Any) -> Optional[str]:
    """Called when a multi-key filename_map lookup fails to find an entry.

    ``parent`` is the map node that was searched (before the failed step), so its keys
    are the valid options to show the user.

    If no plain ``filename`` fallback exists on the arg spec, raises ValueError with the
    invalid key/value and the valid choices. If a fallback exists, returns it silently
    (backward-compatible).
    """
    fallback = arg_spec.get("filename")
    if fallback is None:
        valid = (
            sorted(str(k) for k in parent.keys()) if isinstance(parent, dict) else []
        )
        valid_str = f" Valid values for '{key}': {valid}." if valid else ""
        raise ValueError(
            f"Could not resolve filename for '{arg_spec.get('name', '?')}': "
            f"no entry for {key}={val!r} in filename_map.{valid_str}"
        )
    return fallback


def _resolve_filename(arg_spec: dict, options_context: Dict[str, Any]) -> Optional[Any]:
    """Return filename for an arg spec, preferring filename_map over filename.

    Supports two filename_map formats:

    Single-key (existing):
        filename_map:
          <option-name>:
            <option-value>: <filename>

    Multi-key (new):
        filename_map:
          keys: [key1, key2, ...]
          map:
            <key1-value>:
              <key2-value>: <filename>

    For multi-key format, if the final lookup key's value is a list (e.g.
    ``region: [ALL, WAIS]``), iterates and returns a list of filenames.
    Tolerates int vs. string key mismatches (YAML may parse ``2300`` as int).

    Falls back to ``filename`` if the map is absent or a key isn't in the map.
    For multi-key format without a ``filename`` fallback, raises ValueError on
    a miss so the user sees which values are valid.
    """
    filename_map = arg_spec.get("filename_map")
    if not filename_map or not isinstance(filename_map, dict):
        return arg_spec.get("filename")

    # --- Multi-key format ---
    if "keys" in filename_map:
        current = filename_map.get("map", {})
        for key in filename_map["keys"]:
            val = options_context.get(key) or options_context.get(key.replace("-", "_"))
            if val is None:
                return arg_spec.get("filename")
            if isinstance(val, list):
                # Iterate over list values and collect one filename per element.
                results = []
                for v in val:
                    node = _map_get(current, v)
                    if node is not None and not isinstance(node, dict):
                        results.append(node)
                return (
                    results if results else _multi_key_miss(arg_spec, key, val, current)
                )
            parent = current
            current = _map_get(current, val)
            if current is None:
                return _multi_key_miss(arg_spec, key, val, parent)
            if not isinstance(current, dict):
                return current
        return arg_spec.get("filename")

    # --- Single-key format ---
    for option_name, value_map in filename_map.items():
        if not isinstance(value_map, dict):
            continue
        option_value = options_context.get(option_name) or options_context.get(
            option_name.replace("-", "_")
        )
        if isinstance(option_value, list):
            # Single-key format doesn't support list values — skip to avoid TypeError.
            continue
        if option_value is not None and option_value in value_map:
            return value_map[option_value]
    return arg_spec.get("filename")


def _options_defaults_from_schema(options_specs: list[dict]) -> Dict[str, Any]:
    """Extract {option-name: default_value} from the schema's options specs.

    Both kebab-case and snake_case keys are included so filename_map lookups work
    regardless of which form appears in the map.
    """
    context: Dict[str, Any] = {}
    for opt_spec in options_specs:
        name = opt_spec.get("name", "")
        if name and "default_value" in opt_spec:
            context[name] = opt_spec["default_value"]
            context[name.replace("-", "_")] = opt_spec["default_value"]
    return context


def _build_options_context(
    schema_defaults: Dict[str, Any],
    prefilled_options: Dict[str, Any],
    top_level_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge options context with priority: top_level < schema defaults <
    prefilled_options.

    Both kebab-case and snake_case forms of prefilled_options keys are included.
    """
    context = {**top_level_context}
    context.update(schema_defaults)
    for k, v in prefilled_options.items():
        context[k] = v
        context[k.replace("-", "_")] = v
    return context


def _build_outputs(
    file_outputs: list[dict],
    other_outputs: list[dict],
    module_name: str,
    options_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the outputs dict for a module spec.

    Raises ValueError if a file output is missing filename/filename_map or output_type.
    """
    outputs: Dict[str, Any] = {}
    for arg_spec in file_outputs:
        arg_name = arg_spec.get("name", "")
        if not arg_name:
            continue
        filename = _resolve_filename(arg_spec, options_context)
        if not filename:
            raise ValueError(
                f"Module {module_name} output '{arg_name}' is missing "
                "a 'filename' or 'filename_map' key in module YAML (arguments.outputs)."
            )
        output_type = arg_spec.get("output_type", "")
        if not output_type:
            raise ValueError(
                f"Module {module_name} output '{arg_name}' is missing "
                "required 'output_type' key in module YAML (arguments.outputs)."
            )
        if isinstance(filename, list):
            outputs[arg_name] = {
                "value": [f"{module_name}/{f}" for f in filename],
                "output_type": output_type,
            }
        else:
            outputs[arg_name] = {
                "value": f"{module_name}/{filename}",
                "output_type": output_type,
            }
    for arg_spec in other_outputs:
        arg_name = arg_spec.get("name", "")
        if not arg_name:
            continue
        outputs[arg_name] = {"value": module_name}
    return outputs


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
        name = field_spec.get("name", "")
        if not name:
            continue
        clue = field_spec.get("help", f"Add your {name} here.")
        bundle = create_metadata_bundle(clue, prefilled_values.get(name))
        default_value = field_spec.get("default_value")
        if default_value:
            bundle["default_value"] = default_value
            if bundle.get("value") is None:
                bundle["value"] = default_value
            logger.info("default: %s", default_value)

        if include_filename:
            filename = _resolve_filename(field_spec, options_context)
            if filename:
                bundle["filename"] = filename
                if (
                    isinstance(filename, list)
                    and field_spec.get("multiple", False)
                    and bundle.get("value") is None
                ):
                    bundle["value"] = filename
            logger.info("filename: %s", filename)
        result[name] = bundle

    return result


@dataclass
class ModuleExperimentSpec:
    """In-memory representation of one module's section in experiment-config.yaml.

    Serializes to a nested {"values": ..., "schema": ...} dict:
        values.inputs:  {field_name: clue/value-bundle-or-plain-value}
        values.options: {field_name: clue/value-bundle-or-plain-value}
        values.fingerprint_params: ...
        values.outputs: {output_name: {"value": path, "output_type": ...}}
        values.image:   str (container image URL)
        schema: the frozen ModuleSchema consulted from the registry at
            setup-experiment time (see ModuleSchema.to_dict()) — carried here
            so generate-compose never needs a live registry.
    """

    module_name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    fingerprint_params: Dict[str, Any] = field(default_factory=dict)
    image: str = ""
    schema: Optional[ModuleSchema] = None

    # Constructors
    @classmethod
    def from_module_schema(
        cls,
        module_schema: ModuleSchema,
        prefilled_inputs: Optional[Dict[str, str]] = None,
        prefilled_options: Optional[Dict[str, Any]] = None,
        top_level_context: Optional[Dict[str, Any]] = None,
    ) -> "ModuleExperimentSpec":
        """Build an initial spec with clue,value,default,filename placeholders.

        Args:
            module_schema: The base module schema.
            prefilled_inputs: Input values to pre-fill (e.g. climate_data_file).
            prefilled_options: Option values to write as plain values instead of
                clue/value bundles (e.g. {"region": ["RGI01", "RGI02"]} or
                {"region": "RGI01"}).  List values are included in options_context
                so multi-key filename_map resolution can iterate over them.
            top_level_context: Top-level experiment params (e.g. {"pyear_end": 2300})
                seeded into options_context at lowest priority, allowing multi-key
                filename_map lookups that span top-level and module-level keys.
        """
        prefilled_inputs = prefilled_inputs or {}
        prefilled_options = prefilled_options or {}

        options_context = _build_options_context(
            schema_defaults=_options_defaults_from_schema(
                module_schema.arguments.get("options", [])
            ),
            prefilled_options=prefilled_options,
            top_level_context=top_level_context or {},
        )

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
        # Overwrite clue/value bundles with pre-supplied plain values where provided.
        for k, v in prefilled_options.items():
            if k in options:
                options[k] = v

        fingerprint_params = _build_section_from_fields(
            module_schema.arguments.get("fingerprint_params", []),
            include_filename=True,
            options_context=options_context,
        )

        module_outputs = _build_outputs(
            file_outputs=module_schema.get_file_outputs(),
            other_outputs=module_schema.get_other_outputs(),
            module_name=module_schema.module_name,
            options_context=options_context,
        )

        return cls(
            module_name=module_schema.module_name,
            inputs=module_inputs,
            options=options,
            outputs=module_outputs,
            fingerprint_params=fingerprint_params,
            image=module_schema.container_image,
            schema=module_schema,
        )

    @classmethod
    def from_dict(cls, module_name: str, d: Dict[str, Any]) -> "ModuleExperimentSpec":
        values = d.get("values") or {}
        schema_dict = d.get("schema")
        return cls(
            module_name=module_name,
            inputs=dict(values.get("inputs") or {}),
            options=dict(values.get("options") or {}),
            outputs=dict(values.get("outputs") or {}),
            fingerprint_params=dict(values.get("fingerprint_params") or {}),
            image=values.get("image", ""),
            schema=ModuleSchema.from_dict(schema_dict) if schema_dict else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to the nested {"values": ..., "schema": ...} shape used in
        experiment-config.yaml."""
        values: Dict[str, Any] = {
            "inputs": dict(self.inputs),
            "options": dict(self.options),
            "image": self.image,
            "outputs": dict(self.outputs),
        }
        if self.fingerprint_params:
            values["fingerprint_params"] = dict(self.fingerprint_params)
        d: Dict[str, Any] = {"values": values}
        if self.schema is not None:
            d["schema"] = self.schema.to_dict()
        return d
