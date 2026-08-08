from typing import Dict
from dataclasses import dataclass
import dataclasses
from pathlib import Path
import logging

# ---------------- Core imports ---------------
from facts_experiment_builder.core.experiment.experiment import (
    TopLevelParams,
)
from facts_experiment_builder.core.experiment.skeleton import (
    ExperimentSkeleton,
    parse_module_regions,
)
from facts_experiment_builder.core.experiment.skeleton import (
    experiment_skeleton_to_facts_experiment,
)

# --------------- IO imports --------------
from facts_experiment_builder.core.experiment.name import (
    ExperimentName,
)

from facts_experiment_builder.io.paths import (
    ExperimentPaths,
    make_output_dir,
)
from facts_experiment_builder.io.module_registry import (
    ModuleRegistry,
)
from facts_experiment_builder.io.experiment_repository import ExperimentRepository

logger = logging.getLogger(__name__)


@dataclass
class PrepareExperimentOutput:
    """Object to hold output of prepare_experiment_setup()."""

    experiment_paths: ExperimentPaths
    experiment_skeleton: ExperimentSkeleton


def make_experiment_paths(
    experiment_name: str,
    workspace_dir: Path,
) -> ExperimentPaths:
    # Create an experiment name object
    experiment_name_obj = ExperimentName.parse(raw_name=experiment_name)

    # Create experiment path from resolved root (handled in cli layer)
    experiment_path_obj = ExperimentPaths(
        workspace_dir=workspace_dir, experiment_name=experiment_name_obj
    )
    # Make direcotries related to this experiment
    make_output_dir(experiment_paths=experiment_path_obj)
    return experiment_path_obj


def make_skeleton(
    module_regions: str,
    climate_step: str,
    supplied_climate_step_data: Path,
    sealevel_step: str,
    supplied_totaled_sealevel_step_data: Path,
    extremesealevel_step: str,
) -> PrepareExperimentOutput:
    """Performs first stage of experiment setup and creates ExperimentSkeleton.

    Parses requested experiment name and resolves experiment's directory layout. Calls io.make_output_dir() to create direcotories. Parses module regions, if applicable and builds an :class:`ExperimentSkeleton` from supplied step configuration. Execution stops before workflows are assembled (this step requires user input). Returned paths and skeleton are passed to :func:`finalize_experiment_setup`.

    Parameters
    ----------
    module_regions: str
        Unparsed module-to-region specification, expanded by :fun:`parse_module_regions`.
    climate_step: str
        Name of module to run at the climate step of the experiment
    supplied_climate_step_data: Path
        Path to data to use in place of running module at climate step.
    sealevle_step: str
        Name(s) of modules to run at the sea-level step of the experiment
    supplied_totaled_sealevel_step_data: Path
        Path to data to use in place of running modules at sea-level step of experiment.
    extremesealevel_step: str
        Name of module to run at extreme sealevel-module step of experiment.

    Returns
    -------
    PrepareExperimentOutput
        Bundle containing the :class:`ExperimentPaths` for the experiment and the :class:`ExperimentSkeleton` built from the step configuration.
    """
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

    return skeleton


def finalize_experiment_setup(
    experiment_name: str,
    experiment_paths: ExperimentPaths,
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
    shared_input_data: str,
    projection_scale: str,
    registry: ModuleRegistry,
    experiment_storage: ExperimentRepository,
) -> Path:
    """Complete an experiment setup and writes its configuration metadata to disk.

    This is the final stage of the experiment setup flow. It pulls module version and schema information from ``registry``, assembles the top-level runtime parameters, attaches the resolved workflows to an existing :class:`ExperimentSkeleton`, converts the result into a concrete ``FactsExperiment``, and renders the experiment configuration YAML.

    Parameters
    ----------
    experiment_name : str
        Human-readable name of the experiment, recorded in the config file.
    experiment_paths : ExperimentPaths
        Container holding the resolved filesystem locations for hte experiment, including the experiment directory and the configuration file path.
    experiment_skeleton : ExperimentSkeleton
        Paritally populated experiment descriptino produced in prepare_exerpiment_setup(). Supplies module names, and any climate or supplied totaled sea-level step data.
    workflows_dict : Dict
        Mapping of workflow names to their definitions, attached to a copy of ``experiment_skeleton``.
    pipeline_id : str
        Identifier of the pipeline this experiment belongs to.
    scenario : str
        Name of emissions or forcing scenario being projected
    baseyear : int
        Reference year against which projections are computed.
    pyear_start : int
        First year of projection time series
    pyear_end : int
        Last year of projection time series
    pyear_step : int
        Interval (in years) of projection time series
    nsamps : int
        Number of samples to generate
    location_file : str
        Path to location file used in experiment
    module_specific_input_data : str
        Path to module-specific input data
    shared_input_data : str
        Path to input data shared across modules
    projection_scale : str
        Indicates whether this experiment generates global (GMSL) or local (RSL) projections of sea level change.
    registry : ModuleRegistry
        Source of module metadata. Queried for the module registry version and schema of each module named in ``experiment_skeleton``.

    Returns
    -------
    Path
        Path to the experiment config file written in this function
    See Also
    --------
    experiment_skeleton_to_facts_experiment : Builds the concrete experiment object.
    write_config_jinja2 : Renders the configuration file from a template.

    Notes
    -----
    ``experiment_skeleton`` is not mutated; :func:`dataclasses.replace` is used to
    produce a copy carrying ``workflows_dict``. Experiment-specific input data is
    collected from the skeleton's climate and supplied sea-level step fields, with
    ``None`` entries dropped, so an experiment supplying neither yields an empty list.
    """
    # Gather info from port
    version = registry.version()
    schemas = {m: registry.get_schema(m) for m in experiment_skeleton.all_module_names}
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

    # handle exp specific data
    experiment_spec_data = [
        experiment_skeleton.climate_data,
        experiment_skeleton.supplied_totaled_sealevel_step_data,
    ]
    experiment_spec_data = [i for i in experiment_spec_data if i is not None]
    # Create FactsExperiment from template
    experiment_obj = experiment_skeleton_to_facts_experiment(
        experiment_name=experiment_name,
        skeleton=skeleton_with_workflows,
        top_level_params=top_level_params,
        experiment_path=experiment_paths.experiment_dir,
        module_specific_input_data=module_specific_input_data,
        experiment_specific_input_data=experiment_spec_data,  # supplied_climate_step_data,
        shared_input_data=shared_input_data,
        projection_scale=projection_scale,
        schemas=schemas,
    )

    config_path = experiment_paths.config_path

    experiment_storage.add(
        experiment=experiment_obj,
        config_path=config_path,
        module_registry_version=version,
    )
    return config_path
    # write_config_jinja2(experiment_config=experiment_config, config_path=config_path)
    # return config_path
