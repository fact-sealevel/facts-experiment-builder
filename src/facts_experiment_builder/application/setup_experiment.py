from typing import Dict, List, Optional

from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)
from facts_experiment_builder.core.registry import ModuleRegistry
from facts_experiment_builder.core.module.module_schema import (
    collect_metadata_param_keys,
)
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)
from facts_experiment_builder.core.experiment.module_name_validation import (
    validate_module_names,
)
from facts_experiment_builder.core.experiment import FactsExperiment
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
)
from facts_experiment_builder.core.steps import (
    ClimateStep,
    SealevelStep,
    TotalingStep,
    ExtremeSealevelStep,
)
from facts_experiment_builder.infra.module_loader import (
    load_facts_module_by_name,
)
from facts_experiment_builder.infra.experiment_manager import (
    resolve_experiment_directory_path,
    check_if_experiment_directory_exists,
    create_experiment_directory,
    create_experiment_directory_files,
)


def _climate_output_file_path(climate_module_name: str) -> Optional[str]:
    """Return the output climate file path for a climate module (e.g. 'fair-temperature/climate.nc')."""
    schema = load_facts_module_by_name(climate_module_name)
    for output in schema.get_file_outputs():
        if output.get("name") == "output-climate-file":
            filename = output.get("filename", "climate.nc")
            return f"{climate_module_name}/{filename}"
    return None


def validate_skeleton_modules(skeleton: ExperimentSkeleton):
    """Checks that all modules in the experiment skeleton are valid."""
    valid = ModuleRegistry.default().list_modules()
    try:
        validate_module_names(skeleton.all_module_names, valid)
    except ValueError as e:
        raise ValueError(
            f"{e}\nCheck for typos or run 'uv run list-modules' to see available modules."
        ) from e


def hydrate_sealevel_step(skeleton) -> SealevelStep:
    if skeleton.sealevel_modules:
        sealevel_schemas = [
            load_facts_module_by_name(m) for m in skeleton.sealevel_modules
        ]
        climate_data_file = skeleton.climate_data

        sealevel_step = SealevelStep.from_module_schemas(
            sealevel_schemas, climate_data_file=climate_data_file
        )
    else:
        sealevel_step = SealevelStep(
            supplied_totaled_sealevel_data=skeleton.supplied_totaled_sealevel_step_data,
        )

    return sealevel_step


def hydrate_experiment(skeleton: ExperimentSkeleton) -> tuple:
    """Load module YAMLs from an ExperimentSkeleton and return the four hydrated steps.

    Errors from unknown module names propagate immediately — no silent failures.
    """
    if skeleton.climate_module and skeleton.climate_module.upper() != "NONE":
        climate_step = ClimateStep.from_module_schema(
            load_facts_module_by_name(skeleton.climate_module)
        )
    elif skeleton.supplied_totaled_sealevel_step_data:
        climate_step = ClimateStep.not_needed()
    else:
        climate_step = ClimateStep(alternate_climate_data=skeleton.climate_data)

    sealevel_step = hydrate_sealevel_step(skeleton)

    if skeleton.totaling_module:
        totaling_step = TotalingStep.from_module_schema(
            load_facts_module_by_name(skeleton.totaling_module)
        )
    else:
        totaling_step = TotalingStep()

    if skeleton.extremesealevel_module:
        extreme_sealevel_step = ExtremeSealevelStep.from_module_schema(
            load_facts_module_by_name(skeleton.extremesealevel_module)
        )
    else:
        extreme_sealevel_step = ExtremeSealevelStep()

    return climate_step, sealevel_step, totaling_step, extreme_sealevel_step


def setup_experiment_fs(
    experiment_name: str,
):
    """Given an experiment name, resolves path to the sub-directory for that experiment.
    Raises an error if the sub-directory already exists."""
    # Resolve the experiment directory path
    experiment_path = resolve_experiment_directory_path(experiment_name)
    # Raise error if it already exists
    if check_if_experiment_directory_exists(experiment_path):
        raise ExperimentAlreadyExistsError(
            path=experiment_path, experiment_name=experiment_name
        )
    return experiment_path


def populate_experiment_directory(experiment_path: str, module_names: List[str]):
    """Creates sub-directory in experiments/ for this experiment.
    Also prepopulates with _____"""
    # Create the experiment directory
    create_experiment_directory(experiment_path)
    # Create the experiment directory files
    create_experiment_directory_files(experiment_path, module_names)

    return


def experiment_skeleton_to_facts_experiment(
    experiment_name: str,
    skeleton: ExperimentSkeleton,
    pipeline_id: Optional[str] = None,
    scenario: Optional[str] = None,
    baseyear: Optional[int] = None,
    pyear_start: Optional[int] = None,
    pyear_end: Optional[int] = None,
    pyear_step: Optional[int] = None,
    nsamps: Optional[int] = None,
    location_file: Optional[str] = None,
    module_specific_input_data: Optional[str] = None,
    experiment_specific_input_data: Optional[str] = None,
    shared_input_data: Optional[str] = None,
) -> FactsExperiment:
    """
    Load module YAMLs from a skeleton and assemble a fully-formed FactsExperiment.

    Unknown module names raise FileNotFoundError — no silent failures.
    """

    # validate skeleton first
    validate_skeleton_modules(skeleton)

    # hydrate skeleton to create steps
    climate_step, sealevel_step, totaling_step, extreme_sealevel_step = (
        hydrate_experiment(skeleton)
    )

    # Load schemas to derive which top-level and fingerprint keys this experiment needs
    schemas = [load_facts_module_by_name(m) for m in skeleton.all_module_names]

    # Lookup table mapping schema key names (kebab and snake) to CLI-provided values
    cli_values: Dict[str, object] = {
        "pipeline-id": pipeline_id,
        "pipeline_id": pipeline_id,
        "scenario": scenario,
        "baseyear": baseyear,
        "pyear_start": pyear_start,
        "pyear-start": pyear_start,
        "pyear_end": pyear_end,
        "pyear-end": pyear_end,
        "pyear_step": pyear_step,
        "pyear-step": pyear_step,
        "nsamps": nsamps,
        "location-file": location_file,
        "location_file": location_file,
    }

    ## This section is for top-level / experiment-level fields
    # it extracts information for top-level params from module yamls
    # and has fixed fields for experiment level params like paths
    top_level_keys = collect_metadata_param_keys(schemas, "top_level")
    top_level_params = {
        key: create_metadata_bundle(help_text, cli_values.get(key))
        for key, help_text in top_level_keys.items()
    }

    paths = {
        "module-specific-input-data": create_metadata_bundle(
            "Module-specific input data", module_specific_input_data
        ),
        "shared-input-data": create_metadata_bundle(
            "Shared input data", shared_input_data
        ),
        "experiment-specific-input-data": create_metadata_bundle(
            "Experiment-specific input data (eg. alternative FAIR data)",
            experiment_specific_input_data,
        ),
        "output-data-location": create_metadata_bundle(
            "Output path",
            f"./experiments/{experiment_name}/data/output",
        ),
        **(
            {
                "supplied-totaled-sealevel-step-data": create_metadata_bundle(
                    "Path to pre-existing totaled sealevel data (replaces running climate and sealevel modules)",
                    skeleton.supplied_totaled_sealevel_step_data,
                )
            }
            if skeleton.supplied_totaled_sealevel_step_data
            else {}
        ),
    }

    fp_keys = collect_metadata_param_keys(schemas, "fingerprint_params")
    fingerprint_params = {
        key: create_metadata_bundle(help_text, cli_values.get(key))
        for key, help_text in fp_keys.items()
    }

    return FactsExperiment(
        experiment_name=experiment_name,
        top_level_params=top_level_params,
        climate_step=climate_step,
        sealevel_step=sealevel_step,
        totaling_step=totaling_step,
        extreme_sealevel_step=extreme_sealevel_step,
        paths=paths,
        fingerprint_params=fingerprint_params,
        workflows=skeleton.workflows,
    )
