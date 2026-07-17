"""Build ModuleServiceSpec instances from experiment metadata and module YAML."""

from pathlib import Path
from typing import Dict, Any, Set, List, Optional
import os

from facts_experiment_builder.infra.path_utils import (
    expand_path,
    resolve_input_path,
    resolve_output_path,
    build_module_input_paths,
    build_module_output_paths,
)

from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleContainerImage,
    ModuleSchema,
)
from facts_experiment_builder.core.typed_path import (
    HostPath,
    HostDirPath,
    ContainerPath,
    ExperimentSpecificInputPath,
)


class InvalidModuleTypeError(Exception):
    def __init__(
        self,
        module_type: str,
    ):
        self.module_type = module_type
        super().__init__(
            f"Received invalid module type '{module_type}'."
            f"Module type must be None or one of: {', '.join(sorted(ALLOWED_MODULE_TYPES))}"
        )


ALLOWED_MODULE_TYPES = frozenset(
    {
        "temperature_module",
        "sealevel_module",
        "framework_module",
        "extreme_sealevel_module",
        "other_module",
    }
)


def get_required_field(
    metadata: Dict[str, Any], field_name: str, context: str = ""
) -> Any:
    """
    Get a required field from metadata, raising an error if missing.

    Args:
        metadata: Metadata dictionary
        field_name: Name of the field to extract
        context: Optional context for error message (e.g., module name)

    Returns:
        Field value

    Raises:
        KeyError: If field is missing
    """
    if field_name not in metadata:
        context_msg = f" in {context}" if context else ""
        raise KeyError(
            f"Required field '{field_name}' is missing from metadata{context_msg}. Instead, saw {metadata.keys()}"
        )
    return metadata[field_name]


def get_required_field_with_alternatives(
    metadata: Dict[str, Any],
    primary_field: str,
    alternative_fields: List[str],
    context: str = "",
) -> Any:
    """
    Get a required field, trying primary first, then alternatives.

    Args:
        metadata: Metadata dictionary
        primary_field: Primary field name to try first
        alternative_fields: List of alternative field names to try
        context: Optional context for error message

    Returns:
        Field value from first found field

    Raises:
        KeyError: If none of the fields are present
    """
    # Try primary field first
    if primary_field in metadata:
        return metadata[primary_field]

    # Try alternatives
    for alt_field in alternative_fields:
        if alt_field in metadata:
            return metadata[alt_field]

    # None found
    # all_fields = [primary_field] + alternative_fields
    context_msg = f" in {context}" if context else ""
    raise KeyError(
        f"Required field '{primary_field}' (or alternatives: {', '.join(alternative_fields)}) "
        f"is missing from metadata{context_msg}"
    )


def get_experiment_paths(metadata: Dict[str, Any], context: str = "") -> Dict[str, str]:
    """
    Extract experiment-level paths from metadata.

    Args:
        metadata: Experiment metadata dictionary
        context: Optional context for error messages

    Returns:
        Dictionary with keys:
        - 'shared_input_data': Path to shared input data
        - 'module_specific_input_data': Path to module-specific input data
        - 'output_data_location': Path to output data location

    Raises:
        KeyError: If required paths are missing from metadata
        ValueError: If path values are None or invalid
    """
    shared_input_data = get_required_field_with_alternatives(
        metadata, "shared-input-data", ["shared_input_data"], context
    )
    if shared_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'shared-input-data' (or 'shared_input_data') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(shared_input_data, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'shared-input-data' has invalid type: expected str, got {type(shared_input_data)}{context_msg}"
        )

    module_specific_input_data = get_required_field_with_alternatives(
        metadata, "module-specific-input-data", ["module_specific_input_data"], context
    )
    if module_specific_input_data is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'module-specific-input-data' (or 'module_specific_input_data') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(module_specific_input_data, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'module-specific-input-data' has invalid type: expected str, got {type(module_specific_input_data)}{context_msg}"
        )

    output_data_location = get_required_field_with_alternatives(
        metadata,
        "output-data-location",
        ["output_data_location", "output-path", "output_path"],
        context,
    )
    if output_data_location is None:
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'output-data-location' (or alternatives: 'output_data_location', 'output-path', 'output_path') is None{context_msg}. "
            f"Please provide a valid path string."
        )
    if not isinstance(output_data_location, str):
        context_msg = f" in {context}" if context else ""
        raise ValueError(
            f"Required path field 'output-data-location' has invalid type: expected str, got {type(output_data_location)}{context_msg}"
        )

    return {
        "shared_input_data": shared_input_data,
        "module_specific_input_data": module_specific_input_data,
        "output_data_location": output_data_location,
    }


def _dir_input_keys(module_definition: Any) -> Set[str]:
    """Return set of input field names declared as directory paths (type: 'dir') in the module YAML."""
    keys: Set[str] = set()
    for arg_spec in module_definition.arguments.get("inputs", []):
        if arg_spec.get("type") != "dir":
            continue
        source = arg_spec.get("source", "")
        if "." in source:
            keys.add(source.split(".")[-1])
    return keys


def _multiple_file_input_keys(module_definition: Any) -> Set[str]:
    """Return set of input field names that are multiple file inputs (from module YAML)."""
    keys: Set[str] = set()
    for arg_spec in module_definition.arguments.get("inputs", []):
        if not arg_spec.get("multiple", False):
            continue
        if not (arg_spec.get("mount") or arg_spec.get("type") == "file"):
            continue
        source = arg_spec.get("source", "")
        if "." in source:
            field = source.split(".")[-1]
            keys.add(field)
    return keys


def module_type_is_valid(module_type: Optional[str]) -> bool:
    return module_type is None or module_type in ALLOWED_MODULE_TYPES


def build_module_service_spec(
    metadata: Dict[str, Any],
    # experiment_dir: Path,
    module_name: str,
    known_module_names: List,
    module_definition: ModuleSchema,
    module_type: str = None,
) -> ModuleServiceSpec:
    """
    Build a ModuleServiceSpec for the given module from experiment metadata and module YAML.

    Args:
        metadata: Experiment metadata dictionary
        experiment_dir: Path to experiment directory
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets')
        module_type: Optional category (e.g. 'temperature_module', 'sealevel_module')

    Returns:
        ModuleServiceSpec instance
    """
    if not module_type_is_valid(module_type=module_type):
        raise InvalidModuleTypeError(
            module_type=module_type,
        )

    module_context = f"{module_name} module"

    module_metadata = get_required_field(metadata, module_name, module_context)

    scenario_name = get_required_field(metadata, "scenario", module_context)
    if isinstance(scenario_name, dict):
        scenario_name = scenario_name.get(
            "scenario_name", scenario_name.get("scenario")
        )

    experiment_paths = get_experiment_paths(metadata, module_context)

    raw_exp_specific = metadata.get("experiment-specific-input-data")
    if isinstance(raw_exp_specific, dict):
        raw_exp_specific = raw_exp_specific.get("value")
    experiment_specific_input = (
        expand_path(
            raw_exp_specific, f"{module_context} (experiment-specific-input-data)"
        )
        if raw_exp_specific
        else None
    )

    shared_input_data = expand_path(
        experiment_paths["shared_input_data"],
        f"{module_context} (shared-input-data)",
    )

    module_specific_input_base = expand_path(
        experiment_paths["module_specific_input_data"],
        f"{module_context} (module-specific-input-data)",
    )
    # If metadata points at a specific module's dir (e.g. .../fair-temperature), use parent as base
    # so volume host path is always base + current module's suffix only (never another module's name).
    if (
        Path(module_specific_input_base).name in known_module_names
    ):  # registry.module_names():
        module_specific_input_base = str(Path(module_specific_input_base).parent)
    # Module-specific input dir: driven by input_dir_name in module YAML (e.g. "ipccar5" for both
    # ipccar5-glaciers and ipccar5-icesheets). Falls back to module_definition.module_name so that
    # per-workflow service names (e.g. extremesealevel-pointsoverthreshold-wf1) resolve to the base
    # module's dir automatically.
    module_specific_input_path_suffix = module_definition.input_dir_name  # ()
    module_specific_input_data = (
        module_specific_input_base + "/" + module_specific_input_path_suffix
    )

    output_data_partial = expand_path(
        experiment_paths["output_data_location"],
        f"{module_context} (output-data-location)",
    )
    # Only facts-total workflow services (names like facts-total-wf1) use a shared output
    # subdir and optional container base. Other modules are unchanged.
    is_facts_total_workflow = module_name.startswith("facts-total-")
    if is_facts_total_workflow:
        output_data_location = output_data_partial + "/facts-total"
        if not Path(output_data_location).exists():
            os.makedirs(output_data_location, exist_ok=True)
        output_container_base = (
            module_metadata.get("_output_container_base")
            or "/mnt/total_out/facts-total"
        )
    else:
        output_data_location = output_data_partial + "/" + module_name
        if not Path(output_data_location).exists():
            os.makedirs(output_data_location, exist_ok=True)
        output_container_base = None

    module_inputs_section = get_required_field(
        module_metadata, "inputs", module_context
    )
    options_dict = {}
    options_section = module_metadata.get("options", {})
    if isinstance(options_section, dict):
        for key, value in options_section.items():
            if not key.startswith("#"):
                options_dict[key] = value

    # Inputs that mount from the shared output volume produced by another serivce (such as fair-temperature)
    # They're stored as relative paths (ie. fair-temperature/climate.nc -> /mnt/out/fair-temperature/climate.nc)
    # Prev. this was a hard-coded list of the names used for climate-data-file across different module yamls...
    output_root_relative_inputs = module_definition.get_output_volume_input_keys()

    multiple_file_input_keys = _multiple_file_input_keys(module_definition)
    dir_input_keys = _dir_input_keys(module_definition)

    inputs_dict = {}
    for key, value in module_inputs_section.items():
        if key == "input_dir":
            continue
        if key in multiple_file_input_keys:
            # List of already container paths (e.g. facts-total item from generate_compose): do not resolve.
            if (
                isinstance(value, list)
                and value
                and all(str(v).strip().startswith("/mnt/") for v in value if v)
            ):
                inputs_dict[key] = [ContainerPath(str(v).strip()) for v in value if v]
                continue
            # Multiple file inputs with host paths (e.g. gwd_file): resolve each path, wrap as HostPath
            if isinstance(value, list):
                items = [v for v in value if v is not None and str(v).strip()]
            else:
                actual = value.get("value", value) if isinstance(value, dict) else value
                if isinstance(actual, list):
                    items = [v for v in actual if v is not None and str(v).strip()]
                else:
                    items = (
                        [actual] if actual is not None and str(actual).strip() else []
                    )
            resolved = []
            for item in items:
                item_value = item if isinstance(item, (str, dict)) else {"value": item}
                try:
                    resolved.append(
                        resolve_input_path(
                            key,
                            item_value,
                            shared_input_data,
                            module_specific_input_data,
                            module_name,
                            module_context,
                        )
                    )
                except (ValueError, KeyError, TypeError) as e:
                    error_msg = str(e)
                    if "None" in error_msg or "NoneType" in error_msg:
                        raise ValueError(
                            f"Input field '{key}' in {module_context} has None value or None in path resolution. "
                            f"Original error: {error_msg}. "
                            f"Check that '{key}' has a valid value in metadata.{module_name}.inputs"
                        ) from e
                    resolved.append(
                        item_value.get("value", item_value)
                        if isinstance(item_value, dict)
                        else item_value
                    )
            inputs_dict[key] = [HostPath(p) for p in resolved]
            continue
        if isinstance(value, list):
            # e.g. facts-total inputs.item: list of container paths (/mnt/total_out/...)
            inputs_dict[key] = [ContainerPath(str(v).strip()) for v in value if v]
            continue
        if isinstance(value, str) or (isinstance(value, dict) and "value" in value):
            actual = (
                value.get("value", value) if isinstance(value, dict) else value
            ) or ""
            if (
                key in output_root_relative_inputs
                and isinstance(actual, str)
                and actual.strip()
                and not actual.strip().startswith("/")
                and ".." not in actual
            ):
                inputs_dict[key] = actual.strip()  # e.g. "fair-temperature/climate.nc"
                continue
            if (
                key in output_root_relative_inputs
                and isinstance(actual, str)
                and actual.strip().startswith("/")
                and experiment_specific_input
            ):
                inputs_dict[key] = ExperimentSpecificInputPath(actual.strip())
                continue
            try:
                resolved_path = resolve_input_path(
                    key,
                    value,
                    shared_input_data,
                    module_specific_input_data,
                    module_name,
                    module_context,
                )
                inputs_dict[key] = (
                    HostDirPath(resolved_path)
                    if key in dir_input_keys
                    else HostPath(resolved_path)
                )
            except (ValueError, KeyError, TypeError) as e:
                error_msg = str(e)
                if "None" in error_msg or "NoneType" in error_msg:
                    raise ValueError(
                        f"Input field '{key}' in {module_context} has None value or None in path resolution. "
                        f"Original error: {error_msg}. "
                        f"Check that '{key}' has a valid value in metadata.{module_name}.inputs"
                    ) from e
                if isinstance(value, dict):
                    inputs_dict[key] = value.get("value", value)
                else:
                    inputs_dict[key] = value
        else:
            inputs_dict[key] = value

    for opt_spec in module_definition.arguments.get("options", []):
        source = opt_spec.get("source", "")
        if "module_inputs.inputs." in source and "." in source:
            field = source.split(".")[-1]
            if field not in inputs_dict and field in options_dict:
                inputs_dict[field] = options_dict[field]
    for opt_spec in module_definition.arguments.get("options", []):
        name = opt_spec.get("name", "")
        if name and name not in options_dict and name in inputs_dict:
            options_dict[name] = inputs_dict[name]

    module_outputs = get_required_field(module_metadata, "outputs", module_context)
    outputs_dict = {}
    outputs_config = module_definition.get_outputs_list()

    if isinstance(module_outputs, dict):
        for output_spec in outputs_config:
            output_name = output_spec.get("name", "")
            source = output_spec.get("source", "")
            key = source.split(".")[-1] if "." in source else output_name
            if not output_name or output_name not in module_outputs:
                raise KeyError(
                    f"Output '{output_name}' not found in metadata for {module_context}. "
                    f"Expected one of: {list(module_outputs.keys())}"
                )
            output_value = module_outputs[output_name]
            try:
                resolved_path = resolve_output_path(
                    output_value, output_data_location, module_context
                )
                outputs_dict[key] = resolved_path
            except ValueError:
                outputs_dict[key] = output_value
    elif isinstance(module_outputs, list):
        if outputs_config:
            for i, output_spec in enumerate(outputs_config):
                source = output_spec.get("source", "")
                if "." in source:
                    field_name = source.split(".")[-1]
                    if i < len(module_outputs):
                        output_value = module_outputs[i]
                        try:
                            resolved_path = resolve_output_path(
                                output_value, output_data_location, module_context
                            )
                            outputs_dict[field_name] = resolved_path
                        except ValueError:
                            outputs_dict[field_name] = output_value
                else:
                    if i < len(module_outputs):
                        output_value = module_outputs[i]
                        try:
                            resolved_path = resolve_output_path(
                                output_value, output_data_location, module_context
                            )
                            outputs_dict[f"output_{i}"] = resolved_path
                        except ValueError:
                            outputs_dict[f"output_{i}"] = output_value
        else:
            for i, output in enumerate(module_outputs):
                try:
                    resolved_path = resolve_output_path(
                        output, output_data_location, module_context
                    )
                    outputs_dict[f"output_{i}"] = resolved_path
                except ValueError:
                    outputs_dict[f"output_{i}"] = output
    else:
        raise ValueError(
            f"{module_name}.outputs must be a list or dictionary in {module_context}"
        )
    image_data = get_required_field(module_metadata, "image", module_context)
    if isinstance(image_data, str):
        if ":" in image_data:
            image_url, image_tag = image_data.rsplit(":", 1)
        else:
            image_url = image_data
            image_tag = "latest"
    elif isinstance(image_data, dict):
        image_url = image_data.get("image_url", image_data.get("url", ""))
        image_tag = image_data.get("image_tag", image_data.get("tag", "latest"))
    else:
        raise ValueError(
            f"Invalid image format in {module_context}, received: {image_data}"
        )

    image = ModuleContainerImage(image_url=image_url, image_tag=image_tag)

    input_paths = build_module_input_paths(
        module_specific_input_dir=module_specific_input_data,
        shared_input_dir=shared_input_data,
        module_name=module_name,
    )
    output_type = module_metadata.get("output_type", "")
    output_paths = build_module_output_paths(
        output_data_location, module_name=module_name, output_type=output_type
    )

    fingerprint_params = {
        "location_file": metadata.get("location-file"),
    }
    # Merge module-specific fingerprint params (e.g. fprint_gis_file for emulandice-gris)
    module_fp_section = module_metadata.get("fingerprint_params") or {}
    if isinstance(module_fp_section, dict):
        for k, v in module_fp_section.items():
            actual = v.get("value", v) if isinstance(v, dict) else v
            if actual is not None:
                fingerprint_params[k.replace("-", "_")] = actual
    # Fallback: for module-specific fingerprint params whose value ended up in inputs_dict
    # (e.g. from defaults files that use inputs: instead of fingerprint_params:), check there too.
    for fp_arg in module_definition.arguments.get("fingerprint_params", []):
        source = fp_arg.get("source", "")
        if not source.startswith("module_inputs.fingerprint_params."):
            continue
        fp_key = source.split(".")[-1]
        if fp_key in fingerprint_params:
            continue
        if fp_key in inputs_dict:
            fingerprint_params[fp_key] = inputs_dict[fp_key]
    impl_inputs = ModuleServiceSpecComponents(
        module_name=module_name,
        options=options_dict,
        input_paths=input_paths,
        output_paths=output_paths,
        fingerprint_params=fingerprint_params,
        inputs=inputs_dict,
        outputs=outputs_dict,
        image=image,
        metadata=metadata,
        output_container_base=output_container_base,
    )

    return ModuleServiceSpec(
        components=impl_inputs,
        module_definition=module_definition,
    )
