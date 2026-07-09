from typing import Any, Dict, Optional

from pathlib import Path
from dataclasses import dataclass
import dataclasses
from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
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
from facts_experiment_builder.core.experiment.facts_experiment import (
    FactsExperiment,
    TopLevelParams,
    # ExperimentSpecificInputData
)
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
    parse_module_regions,
)
from facts_experiment_builder.core.steps import (
    ClimateStep,
    SealevelStep,
    TotalingStep,
    ExtremeSealevelStep,
)
from facts_experiment_builder.infra.write_experiment_metadata import (
    write_metadata_yaml_jinja2,
)
from facts_experiment_builder.infra.module_loader import (
    load_module_schema_by_name,
)
from facts_experiment_builder.core.steps.climate_resolver import resolve_climate_file
from facts_experiment_builder.infra.experiment_manager import (
    make_experiment_path_from_experiment_name,
    experiment_directory_exists,
    create_experiment_directory,
    create_experiment_directory_files,
    resolve_experiment_parent_dir,
)
import logging

logger = logging.getLogger(__name__)


def which_experiment_specific_data(climate_step_data, sealevel_step_data):
    if climate_step_data is not None and sealevel_step_data is not None:
        raise ValueError(
            "Received values for both supplied_climate_step_data and "
            " supplied_sealevel_step_data. "
            "Only one of these may be specified and used in an experiment"
        )
    if climate_step_data is not None and sealevel_step_data is None:
        return sealevel_step_data
    if sealevel_step_data is not None and climate_step_data is None:
        return sealevel_step_data


def create_experiment_skeleton(
    climate_step,
    supplied_climate_step_data,
    sealevel_step,
    supplied_totaled_sealevel_step_data,
    extremesealevel_step,
    parsed_module_regions,
):
    # create skeleton obj
    skeleton = ExperimentSkeleton.from_inputs(
        climate_step=climate_step,
        supplied_climate_step_data=supplied_climate_step_data,
        sealevel_step=sealevel_step,
        supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
        extremesealevel_step=extremesealevel_step,
        module_regions=parsed_module_regions,
    )

    return skeleton


def is_totaling_needed(sealevel_step: str) -> bool:
    sealevel_module_ls = parse_module_list_str(s=sealevel_step)

    return len(sealevel_module_ls) > 1


@dataclass
class PrepareExperimentOutput:
    experiment_path: str
    experiment_skeleton: ExperimentSkeleton


def prepare_experiment_setup(
    experiment_name: str,
    module_regions: str,
    climate_step,
    supplied_climate_step_data,
    sealevel_step,
    supplied_totaled_sealevel_step_data,
    extremesealevel_step,
) -> PrepareExperimentOutput:
    """Handles initial experiment setup orchestration logic, through to creating skeleton and until workflows owuld be created (need user prompt for this.)"""
    # first, check that experiment name was passed with parent dir
    check_parent_dir_from_experiment_name(experiment_name=experiment_name)

    # Make experiment path from experiment name
    experiment_path = make_experiment_path_from_experiment_name(
        experiment_name=experiment_name
    )

    # check if experiment already exists
    check_if_experiment_already_exists(path_to_experiment=experiment_path)

    # parse module regions received from cli
    parsed_module_regions = parse_module_regions(module_regions)

    # Create experiment skeleton
    skeleton = create_experiment_skeleton(
        climate_step=climate_step,
        sealevel_step=sealevel_step,
        supplied_climate_step_data=supplied_climate_step_data,
        supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
        extremesealevel_step=extremesealevel_step,
        parsed_module_regions=parsed_module_regions,
    )
    output = PrepareExperimentOutput(
        experiment_path=experiment_path, experiment_skeleton=skeleton
    )
    return output


def finalize_experiment_setup(
    experiment_name,
    experiment_path,
    experiment_skeleton,
    workflows_dict,
    pipeline_id,
    scenario,
    baseyear,
    pyear_start,
    pyear_end,
    pyear_step,
    nsamps,
    location_file,
    module_specific_input_data,
    experiment_specific_input_data,  #: ExperimentSpecificInputData,
    shared_input_data,
    projection_scale,
):
    # make TopLevelParams dataclass
    top_level_params = TopLevelParams(
        scenario=scenario,
        pipeline_id=pipeline_id,
        nsamps=nsamps,
        baseyear=baseyear,
        pyear_end=pyear_end,
        pyear_start=pyear_start,
        pyear_step=pyear_step,
        location_file=location_file,
    )
    skeleton_with_workflows = add_workflows_to_skeleton(
        skeleton=experiment_skeleton, workflows_dict=workflows_dict
    )
    populate_experiment_directory(
        experiment_path=experiment_path,
    )
    # Create FactsExperiment from template
    experiment_obj = experiment_skeleton_to_facts_experiment(
        experiment_name=experiment_name,
        skeleton=skeleton_with_workflows,
        top_level_params=top_level_params,
        module_specific_input_data=module_specific_input_data,
        experiment_specific_input_data=experiment_specific_input_data,  # supplied_climate_step_data,
        shared_input_data=shared_input_data,
        projection_scale=projection_scale,
    )
    # Write metadata file using templtae
    metadata_path = experiment_path / "experiment-config.yaml"
    registry_version = ModuleRegistry.default().get_version()

    write_metadata_yaml_jinja2(
        experiment=experiment_obj,
        output_path=metadata_path,
        module_registry_version=registry_version,
    )


def add_workflows_to_skeleton(
    skeleton: ExperimentSkeleton,
    workflows_dict: Dict,
) -> ExperimentSkeleton:
    skeleton = dataclasses.replace(skeleton, workflows=workflows_dict)
    return skeleton


def validate_skeleton_modules(skeleton: ExperimentSkeleton):
    """Checks that all modules in the experiment skeleton are valid."""
    valid = ModuleRegistry.default().list_modules()
    try:
        validate_module_names(skeleton.all_module_names, valid)
    except ValueError as e:
        raise ValueError(
            f"{e}\nCheck for typos or run 'uv run list-modules' to see available modules."
        ) from e


def hydrate_sealevel_step(
    skeleton,
    sealevel_schemas=None,
    climate_files: Optional[Dict[str, str]] = None,
    top_level_context: Optional[Dict[str, Any]] = None,
) -> SealevelStep:
    if skeleton.sealevel_modules:
        if sealevel_schemas is None:
            sealevel_schemas = [
                load_module_schema_by_name(m) for m in skeleton.sealevel_modules
            ]
        sealevel_step = SealevelStep.from_module_schemas(
            sealevel_schemas,
            climate_files=climate_files,
            module_regions=skeleton.module_regions,
            top_level_context=top_level_context,
        )
    else:
        sealevel_step = SealevelStep(
            supplied_totaled_sealevel_data=skeleton.supplied_totaled_sealevel_step_data,
        )

    return sealevel_step


def hydrate_experiment(
    skeleton: ExperimentSkeleton,
    top_level_context: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Load module YAMLs from an ExperimentSkeleton and return the four hydrated steps.

    Errors from unknown module names propagate immediately — no silent failures.
    """
    climate_files: Optional[Dict[str, str]] = None
    sealevel_schemas = None
    if skeleton.climate_module and skeleton.climate_module.upper() != "NONE":
        climate_schema = load_module_schema_by_name(skeleton.climate_module)
        climate_step = ClimateStep.from_module_schema(climate_schema)
        sealevel_schemas = [
            load_module_schema_by_name(m) for m in (skeleton.sealevel_modules or [])
        ]
        climate_files = {
            s.module_name: resolve_climate_file(
                climate_schema, s.get_climate_output_type()
            )
            for s in sealevel_schemas
            if s.get_climate_output_type()
        }
    elif skeleton.supplied_totaled_sealevel_step_data:
        climate_step = ClimateStep.not_needed()
    else:
        climate_step = ClimateStep(alternate_climate_data=skeleton.climate_data)

    sealevel_step = hydrate_sealevel_step(
        skeleton,
        sealevel_schemas=sealevel_schemas,
        climate_files=climate_files,
        top_level_context=top_level_context,
    )

    if skeleton.totaling_module:
        totaling_step = TotalingStep.from_module_schema(
            load_module_schema_by_name(skeleton.totaling_module)
        )
    else:
        totaling_step = TotalingStep()

    if skeleton.extremesealevel_module:
        extreme_sealevel_step = ExtremeSealevelStep.from_module_schema(
            load_module_schema_by_name(skeleton.extremesealevel_module)
        )
    else:
        extreme_sealevel_step = ExtremeSealevelStep()

    return climate_step, sealevel_step, totaling_step, extreme_sealevel_step


def check_parent_dir_from_experiment_name(experiment_name: str) -> Path:
    # first split parent and experiment name
    try:
        return resolve_experiment_parent_dir(experiment_name=experiment_name)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Parent directory for experiment '{experiment_name}' does not exist."
            "You must ensure this directory exists before trying to create an experiment within it."
        ) from e


def check_if_experiment_already_exists(path_to_experiment: Path) -> None:
    if experiment_directory_exists(experiment_directory=path_to_experiment):
        raise ExperimentAlreadyExistsError(
            path=path_to_experiment,
            # experiment_name=experiment_name
        )


def populate_experiment_directory(
    experiment_path: str,
    #     module_names: List[str],
):
    """Creates sub-directory in experiments/ for this experiment.
    Also prepopulates with _____"""
    # Create the experiment directory
    create_experiment_directory(experiment_path)
    # Create the experiment directory files
    create_experiment_directory_files(
        experiment_path,
        # module_names,
    )

    return


def experiment_skeleton_to_facts_experiment(
    experiment_name: str,
    skeleton: ExperimentSkeleton,
    top_level_params: "TopLevelParams",
    module_specific_input_data: Optional[str] = None,
    experiment_specific_input_data: Optional[str] = None,
    shared_input_data: Optional[str] = None,
    projection_scale: str = "local",
) -> FactsExperiment:
    """
    Load module YAMLs from a skeleton and assemble a fully-formed FactsExperiment.

    Unknown module names raise FileNotFoundError — no silent failures.
    """

    # validate skeleton first
    validate_skeleton_modules(skeleton)
    # Load schemas to derive which top-level and fingerprint keys this experiment needs
    schemas = []
    for m in skeleton.all_module_names:
        logger.info("Loading schema for %s module", m)
        schema = load_module_schema_by_name(m)
        schemas.append(schema)
    # [load_module_schema_by_name(m) for m in skeleton.all_module_names]
    # Lookup table mapping schema key names (kebab and snake) to CLI-provided values
    cli_values: Dict[str, object] = {
        "pipeline-id": top_level_params.pipeline_id,
        "pipeline_id": top_level_params.pipeline_id,
        "scenario": top_level_params.scenario,
        "baseyear": top_level_params.baseyear,
        "pyear_start": top_level_params.pyear_start,
        "pyear-start": top_level_params.pyear_start,
        "pyear_end": top_level_params.pyear_end,
        "pyear-end": top_level_params.pyear_end,
        "pyear_step": top_level_params.pyear_step,
        "pyear-step": top_level_params.pyear_step,
        "nsamps": top_level_params.nsamps,
        "location-file": top_level_params.location_file,
        "location_file": top_level_params.location_file,
    }

    # Build top-level context for multi-key filename_map resolution in module specs.
    top_level_context = {k: v for k, v in cli_values.items() if v is not None}
    # hydrate skeleton to create steps
    climate_step, sealevel_step, totaling_step, extreme_sealevel_step = (
        hydrate_experiment(skeleton, top_level_context=top_level_context)
    )

    ## This section is for top-level / experiment-level fields
    # it extracts information for top-level params from module yamls
    # and has fixed fields for experiment level params like paths
    top_level_keys = collect_metadata_param_keys(schemas, "top_level")
    top_level_param_bundles = {
        key: create_metadata_bundle(help_text, cli_values.get(key))
        for key, help_text in top_level_keys.items()
    }

    # extract experiment specific data paths
    # experiment_specific_climate_path = experiment_specific_input_data._get_path(kind="climate")
    # experiment_specific_sealevel_path = experiment_specific_input_data._get_path(kind="sealevle")

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
            f"./{experiment_name}/data/output",
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
        top_level_params=top_level_param_bundles,
        climate_step=climate_step,
        sealevel_step=sealevel_step,
        totaling_step=totaling_step,
        extreme_sealevel_step=extreme_sealevel_step,
        paths=paths,
        fingerprint_params=fingerprint_params,
        workflows=skeleton.workflows,
        projection_scale=projection_scale,
    )
