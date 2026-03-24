from pathlib import Path

from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)
from facts_experiment_builder.core.experiment import FactsExperiment
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
from typing import List, Dict


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


def setup_new_experiment_fs(
    experiment_name: str,
    module_names: List[str],
):
    # Resolve the experiment directory path
    experiment_path = resolve_experiment_directory_path(experiment_name)
    # Raise error if it already exists
    if check_if_experiment_directory_exists(experiment_path):
        raise ExperimentAlreadyExistsError(
            path=experiment_path, experiment_name=experiment_name
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
        load_facts_module_by_name=load_facts_module_by_name,
        top_level_param_clues=TOP_LEVEL_PARAM_CLUES,
    )


def populate_experiment_defaults(experiment: FactsExperiment, module_name: str) -> None:
    """
    Load defaults from defaults.yml for the module and merge into the experiment (application layer: I/O).
    """
    defaults_yml = load_module_defaults(module_name)

    if not defaults_yml:
        return
    try:
        project_root = Path.cwd()
        module_def = load_facts_module_by_name(module_name, project_root)
    except FileNotFoundError as e:
        raise ValueError(f"Could not load module definition for '{module_name}") from e

    experiment.merge_defaults_for_module(module_name, defaults_yml, module_def)
