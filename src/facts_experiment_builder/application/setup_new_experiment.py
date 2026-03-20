from pathlib import Path

from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.infra.module_loader import (
    load_facts_module_by_name,
)
from facts_experiment_builder.infra.module_defaults_loader import (
    load_module_defaults,
)
from facts_experiment_builder.infra.experiment_manager import (
    resolve_experiment_directory_path,
    check_if_experiment_directory_exists,
    create_experiment_directory,
    create_experiment_directory_files,
)
from facts_experiment_builder.core.experiment import FactsExperiment
from typing import List, Dict

from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
    is_metadata_value,
)


# Mapping of top-level param keys to their clue/help text
# TODO ultimately want to move this to be in each module yaml file (i think)
TOP_LEVEL_PARAM_CLUES = {
    "pipeline-id": "Pipeline ID",
    "scenario": "Emissions scenario name",
    "baseyear": "Base year",
    "pyear_start": "Projection year start",
    "pyear_end": "Projection year end",
    "pyear_step": "Projection year step",
    "nsamps": "Number of samples",
    "seed": "Random seed to use for sampling",
    "module-specific-input-data": "Module-specific input data",
    "general-input-data": "General input data",
    # "location-file-name": "Location file name",
    "output-data-location": "Output path",
}

FINGERPRINT_PARAM_CLUES = {
    "fingerprint-dir": "Name of directory holding GRD fingerprint data",
    "location-file": "Location file name",
}


def get_clue_from_module_yaml(
    module_def: ModuleSchema, arg_type: str, field_name: str
) -> str:
    """
    Extract clue/help text from module definition for a specific field.

    Args:
        module_def: ModuleSchema instance (from module YAML)
        arg_type: Type of argument ('options', 'inputs', 'outputs', 'top_level')
        field_name: Field name to look up

    Returns:
        Help text from module definition, or fallback clue if not found
    """
    # Look through arguments of the specified type
    arg_specs = module_def.arguments.get(arg_type, [])

    for arg_spec in arg_specs:
        # Check if this arg_spec matches the field_name
        source = arg_spec.get("source", "")
        if "." in source:
            source_field = source.split(".")[-1]
            if source_field == field_name:
                # Found matching arg_spec, check for help field
                help_text = arg_spec.get("help", "")
                if help_text:
                    return help_text

    # Fallback: generate clue from field name
    return f"add your {field_name} here"


def setup_new_experiment_fs(
    experiment_name: str,
    module_names: List[str],
):
    # Resolve the experiment directory path
    experiment_path = resolve_experiment_directory_path(experiment_name)
    # Raise error if it already exists
    if check_if_experiment_directory_exists(experiment_path):
        raise ExperimentAlreadyExistsError(
            f"Experiment directory {experiment_path} already exists"
        )

    # Create the experiment directory
    create_experiment_directory(experiment_path)
    # Create the experiment directory files
    create_experiment_directory_files(experiment_path, module_names)

    return experiment_path


def init_new_experiment(
    experiment_name: str,
    temperature_module: str,
    sealevel_modules: List[str],
    framework_modules: List[str] = None,
    extremesealevel_module: str = None,
    experiment_path: Path = None,
    pipeline_id: str = None,
    scenario: str = None,
    baseyear: int = None,
    pyear_start: int = None,
    pyear_end: int = None,
    pyear_step: int = None,
    nsamps: int = None,
    seed: int = None,
    location_file: str = None,
    fingerprint_dir: str = None,
    workflow_dict: Dict[str, str] = None,
    module_specific_inputs: str = None,
    general_inputs: str = None,
) -> FactsExperiment:
    """
    Create a new FactsExperiment from CLI inputs
    Uses FactsExperiment.create_new_experiment_obj with dependencies from this module.
    """
    return FactsExperiment.create_new_experiment_obj(
        experiment_name=experiment_name,
        temperature_module=temperature_module,
        sealevel_modules=sealevel_modules,
        framework_modules=framework_modules,
        extremesealevel_module=extremesealevel_module,
        experiment_path=experiment_path,
        pipeline_id=pipeline_id,
        scenario=scenario,
        baseyear=baseyear,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        nsamps=nsamps,
        seed=seed,
        location_file=location_file,
        fingerprint_dir=fingerprint_dir,
        workflow_dict=workflow_dict,
        module_specific_input_data=module_specific_inputs,
        general_input_data=general_inputs,
        create_metadata_bundle=create_metadata_bundle,
        format_module_from_definition=format_module_from_definition,
        load_facts_module_by_name=load_facts_module_by_name,
        top_level_param_clues=TOP_LEVEL_PARAM_CLUES,
    )


def populate_experiment_defaults(experiment: FactsExperiment, module_name: str) -> None:
    """
    Load defaults from defaults.yml for the module and merge into the experiment (application layer: I/O).
    """
    # Make a dict with defaults read from module's defaults.yml
    defaults_yml = load_module_defaults(module_name)

    if not defaults_yml:
        return
    module_def = None
    try:
        project_root = Path.cwd()
        module_def = load_facts_module_by_name(module_name, project_root)
    except FileNotFoundError as e:
        # Module YAML or project root not found; continue with module_def=None
        raise ValueError(f"Could not load module definition for '{module_name}") from e

    experiment.merge_defaults_for_module(
        module_name,
        defaults_yml,
        module_def,
        create_metadata_bundle=create_metadata_bundle,
        get_clue_from_module_yaml=get_clue_from_module_yaml,
        is_metadata_value=is_metadata_value,
    )


def format_module_from_definition(module_def: ModuleSchema) -> dict:
    """Build metadata dict for one module from its ModuleSchema (inputs, options, outputs, image)."""
    # First build inputs dict
    module_inputs = {}
    for arg_spec in module_def.arguments.get("inputs", []):
        arg_name = arg_spec.get("name", "")
        source = arg_spec.get("source", "")
        if "." in source:
            field_name = source.split(".")[-1]
            clue = get_clue_from_module_yaml(module_def, "inputs", field_name)
            if field_name == "climate_data_file":
                module_inputs[field_name] = create_metadata_bundle(
                    clue, "fair-temperature/climate.nc"
                )  # TODO will need to fix this.
            else:
                module_inputs[field_name] = create_metadata_bundle(clue)

    # Then build options dict
    module_options = {}
    top_level_args = module_def.arguments.get("top_level", [])
    top_level_names = [arg.get("name", "") for arg in top_level_args]
    if top_level_names:
        top_level_str = ", ".join(top_level_names)
        module_options[
            f"# Options inherited from top-level metadata: {top_level_str}"
        ] = None

    # Add module-specific options
    for arg_spec in module_def.arguments.get("options", []):
        arg_name = arg_spec.get("name", "")
        source = arg_spec.get("source", "")
        if "." in source:
            field_name = source.split(".")[-1]
            clue = get_clue_from_module_yaml(module_def, "options", field_name)
            module_options[field_name] = create_metadata_bundle(clue)

    # Build outputs dict from each output spec's 'filename' key (same level as name, type, source, mount, output_type)
    module_outputs = {}
    for arg_spec in module_def.arguments.get("outputs", []):
        arg_name = arg_spec.get("name", "")
        if not arg_name:
            continue
        filename = arg_spec.get("filename")
        if not filename:
            raise ValueError(
                f"Module {module_def.module_name} output '{arg_name}' is missing required 'filename' key in module YAML (arguments.outputs)."
            )
        output_type = arg_spec.get("output_type", "")
        if not output_type:
            raise ValueError(
                f"Module {module_def.module_name} output '{arg_name}' is missing required 'output_type' key in module YAML (arguments.outputs)."
            )
        # Path is module_name/filename so outputs live under the module's output subdir
        module_arg_dict = {
            "value": f"{module_def.module_name}/{filename}",
            "output_type": output_type,
        }
        module_outputs[arg_name] = module_arg_dict

    module_dict = {
        "inputs": module_inputs,
        "options": module_options,
        "image": module_def.container_image,
        "outputs": module_outputs,
    }
    return module_dict
