"""Build ModuleServiceSpec instances from experiment metadata and module YAML."""

from pathlib import Path
from typing import Dict, Any, Optional, Set
import os
from facts_experiment_builder.adapters.adapter_utils import (
    get_required_field,
    get_experiment_paths,
)
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
from facts_experiment_builder.core.module.module_schema import ModuleContainerImage
from facts_experiment_builder.core.typed_path import (
    HostPath,
    ContainerPath,
    ExperimentSpecificInputPath,
)
from facts_experiment_builder.infra.module_loader import (
    load_facts_module_from_yaml,
    find_module_yaml_path,
)

ALLOWED_MODULE_TYPES = {
    "temperature_module",
    "sealevel_module",
    "framework_module",
    "extreme_sealevel_module",
    "other_module",
}

_KNOWN_MODULE_NAMES: "Optional[frozenset]" = None


def _registry_module_names() -> frozenset:
    global _KNOWN_MODULE_NAMES
    if _KNOWN_MODULE_NAMES is None:
        from facts_experiment_builder.core.registry.module_registry import (
            ModuleRegistry,
        )

        _KNOWN_MODULE_NAMES = frozenset(ModuleRegistry.default().list_modules())
    return _KNOWN_MODULE_NAMES


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


def build_module_service_spec(
    metadata: Dict[str, Any],
    experiment_dir: Path,
    module_name: str,
    module_type: str = None,
    module_yaml_path: Path = None,
) -> ModuleServiceSpec:
    """
    Build a ModuleServiceSpec for the given module from experiment metadata and module YAML.

    Args:
        metadata: Experiment metadata dictionary
        experiment_dir: Path to experiment directory
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets')
        module_type: Optional category (e.g. 'temperature_module', 'sealevel_module')
        module_yaml_path: Optional path to module YAML (otherwise discovered by name)

    Returns:
        ModuleServiceSpec instance
    """
    if module_type is not None and module_type not in ALLOWED_MODULE_TYPES:
        raise ValueError(
            f"Invalid module_type '{module_type}'. "
            f"Must be one of: {', '.join(sorted(ALLOWED_MODULE_TYPES))}"
        )

    module_context = f"{module_name} module"

    # TODO fix this
    if module_yaml_path and module_yaml_path.exists():
        resolved_yaml_path = module_yaml_path
        # this is total module step/ workflows
    else:
        # this is climate + sea level module steps
        resolved_yaml_path = find_module_yaml_path(module_name)
    module_definition = load_facts_module_from_yaml(resolved_yaml_path)
    module_metadata = get_required_field(metadata, module_name, module_context)

    scenario_name = get_required_field(metadata, "scenario", module_context)
    if isinstance(scenario_name, dict):
        scenario_name = scenario_name.get(
            "scenario_name", scenario_name.get("scenario", "")
        )
    # experiment_name = get_required_field(metadata, "experiment_name", module_context)
    # scenario = ScenarioConfig(
    #    scenario_name=scenario_name,
    #    description=f"Scenario for {experiment_name}",
    # )

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
    if Path(module_specific_input_base).name in _registry_module_names():
        module_specific_input_base = str(Path(module_specific_input_base).parent)
    # Module-specific input dir: driven by input_dir_name in module YAML (e.g. "ipccar5" for both
    # ipccar5-glaciers and ipccar5-icesheets). Falls back to module_definition.module_name so that
    # per-workflow service names (e.g. extremesealevel-pointsoverthreshold-wf1) resolve to the base
    # module's dir automatically.
    module_specific_input_path_suffix = (
        module_definition.extra.get("input_dir_name") or module_definition.module_name
    )
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
                inputs_dict[key] = HostPath(resolved_path)
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
        raise ValueError(f"Invalid image format in {module_context}")

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
        "fingerprint_dir": metadata.get("fingerprint-dir", "FPRINT"),
        "location_file": metadata.get("location-file", "location.lst"),
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
