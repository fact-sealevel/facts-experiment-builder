from typing import Dict

from dataclasses import dataclass
import dataclasses
from pathlib import Path
from facts_experiment_builder.core.module.module_definition_source import (
    ModuleDefinitionSource,
)
from facts_experiment_builder.core.experiment.facts_experiment import (
    TopLevelParams,
)
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
    parse_module_regions,
)
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.infra.write_experiment_metadata import (
    write_metadata_yaml_jinja2,
)
from facts_experiment_builder.application.experiment_helpers import (
    experiment_skeleton_to_facts_experiment,
)
from facts_experiment_builder.infra.experiment_storage import (
    FileSystemExperimentStorage,
)
import logging

logger = logging.getLogger(__name__)


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
    storage: FileSystemExperimentStorage,
) -> PrepareExperimentOutput:
    """Handles initial experiment setup orchestration logic, through to creating
    skeleton and until workflows owuld be created (need user prompt for this.)"""
    # first, check that experiment name was passed with parent dir

    # Create an experiment name object
    experiment_name_obj = ExperimentName.parse(raw_name=experiment_name)

    # Create experiment path from resolved root (handled in cli layer)
    experiment_path = storage.create(experiment_name_obj)

    parsed_module_regions = parse_module_regions(module_regions)
    # Create experiment skeleton
    skeleton = ExperimentSkeleton.from_inputs(
        climate_step=climate_step,
        supplied_climate_step_data=supplied_climate_step_data,
        sealevel_step=sealevel_step,
        supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
        extremesealevel_step=extremesealevel_step,
        module_regions=parsed_module_regions,
    )

    output = PrepareExperimentOutput(
        experiment_path=experiment_path, experiment_skeleton=skeleton
    )
    return output


def finalize_experiment_setup(
    experiment_name,
    experiment_path: Path,
    experiment_skeleton: ExperimentSkeleton,
    workflows_dict: Dict,
    pipeline_id: str,
    scenario: str,
    baseyear: int,
    pyear_start: int,
    pyear_end: int,
    pyear_step: int,
    nsamps: int,
    location_file: str,
    module_specific_input_data: str,
    experiment_specific_input_data: str,
    shared_input_data: str,
    projection_scale: str,
    definition: ModuleDefinitionSource,
):
    # Gather info from port
    version = definition.version()
    schemas = {
        m: definition.get_schema(m) for m in experiment_skeleton.all_module_names
    }

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

    # Add workflows to the skeleton created in the first top-level setup experiment fn
    skeleton_with_workflows = dataclasses.replace(
        experiment_skeleton, workflows=workflows_dict
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
        schemas=schemas,
    )
    # Write metadata file using templtae
    metadata_path = experiment_path / "experiment-config.yaml"

    write_metadata_yaml_jinja2(
        experiment=experiment_obj,
        output_path=metadata_path,
        module_registry_version=version,
    )
