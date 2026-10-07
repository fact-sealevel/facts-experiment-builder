"""Factory for building ModuleServiceSpec objects from experiment metadata.

Separated from core so that filesystem side-effects (directory creation) live in the
application layer rather than the core domain layer.
"""

from typing import Any

from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.module.module_inputs_outputs import (
    build_module_input_paths,
    build_module_output_paths,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
    get_required_field,
    resolve_module_paths,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
    _assemble_fingerprint_params,
    _parse_image,
    _resolve_module_inputs_dict,
    _resolve_module_outputs_dict,
)
from facts_experiment_builder.io.module_dirs import ensure_module_output_dir


def build_module_service_spec(
    metadata: dict[str, Any],
    module_name: str,
    known_module_names: list,
    module_definition: ModuleSchema,
    data_paths: ExperimentDataPaths,
) -> ModuleServiceSpec:
    """Build a ModuleServiceSpec for the given module from experiment metadata and
    module YAML.

    Args:
        metadata: Experiment metadata dictionary
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets')
        known_module_names: List of all known module names in the experiment
        module_definition: Loaded ModuleSchema for this module
        data_paths: Experiment-level paths from resolve_experiment_data_paths()

    Returns:
        ModuleServiceSpec instance
    """
    module_name_str = f"{module_name} module"

    module_metadata = get_required_field(metadata, module_name, module_name_str)

    resolved_paths = resolve_module_paths(
        data_paths=data_paths,
        module_metadata=module_metadata,
        module_name=module_name,
        module_definition=module_definition,
        known_module_names=known_module_names,
    )
    ensure_module_output_dir(resolved_paths.output_data_location)

    input_paths = build_module_input_paths(
        module_specific_input_dir=resolved_paths.module_specific_input_data,
        shared_input_dir=resolved_paths.shared_input_data,
        module_name=module_name,
    )
    output_type = module_metadata.get("output_type", "")
    output_paths = build_module_output_paths(
        output_dir=resolved_paths.output_data_location,
        module_name=module_name,
        output_type=output_type,
    )

    module_inputs_section = get_required_field(
        module_metadata, "inputs", module_name_str
    )

    options_dict = {}
    options_section = module_metadata.get("options", {})
    if isinstance(options_section, dict):
        for opt_spec in module_definition.arguments.options:
            name = opt_spec.name
            if not name or name not in options_section:
                continue
            options_dict[opt_spec.source.leaf] = options_section[name]

    inputs_dict = _resolve_module_inputs_dict(
        module_definition=module_definition,
        module_name_str=module_name_str,
        module_name=module_name,
        module_inputs_section=module_inputs_section,
        shared_input_data=resolved_paths.shared_input_data,
        module_specific_input_data=resolved_paths.module_specific_input_data,
        experiment_specific_input_data=resolved_paths.experiment_specific_input_data,
    )
    for opt_spec in module_definition.arguments.options:
        source = opt_spec.source
        key = source.leaf
        if (
            source.root == "module_inputs"
            and source.attr == "inputs"
            and key not in inputs_dict
            and key in options_dict
        ):
            inputs_dict[key] = options_dict[key]
        elif key not in options_dict and key in inputs_dict:
            options_dict[key] = inputs_dict[key]

    module_outputs = get_required_field(module_metadata, "outputs", module_name_str)

    outputs_dict = _resolve_module_outputs_dict(
        module_definition=module_definition,
        module_outputs=module_outputs,
        module_name_str=module_name_str,
        module_name=module_name,
        output_data_location=resolved_paths.output_data_location,
    )

    image_data = get_required_field(module_metadata, "image", module_name_str)
    image = _parse_image(image_data, module_name_str)

    top_level_params = TopLevelParams.from_config(metadata)
    location_file = top_level_params.location_file
    module_fp_section = module_metadata.get("fingerprint_params") or {}
    fingerprint_params = _assemble_fingerprint_params(
        module_definition=module_definition,
        module_fp_section=module_fp_section,
        location_file=location_file,
    )

    impl_inputs = ModuleServiceSpecComponents(
        module_name=module_name,
        options=options_dict,
        input_paths=input_paths,
        output_paths=output_paths,
        fingerprint_params=fingerprint_params,
        inputs=inputs_dict,
        outputs=outputs_dict,
        image=image,
        top_level_params=top_level_params,
        output_container_base=resolved_paths.output_container_base,
    )

    return ModuleServiceSpec(
        components=impl_inputs,
        module_definition=module_definition,
    )
