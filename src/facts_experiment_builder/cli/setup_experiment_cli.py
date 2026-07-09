"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_experiment.py.

"""

from pathlib import Path
import click
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.setup_experiment import (
    is_totaling_needed,
    prepare_experiment_setup,
    finalize_experiment_setup,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from facts_experiment_builder.core.experiment.experiment_skeleton import (
        ExperimentSkeleton,
    )
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
    unparse_module_list,
    validate_module_names,
)
from facts_experiment_builder.core.registry.module_registry import ModuleRegistry
from facts_experiment_builder.core.experiment.facts_experiment import (
    ExperimentSpecificInputData,
)
from facts_experiment_builder.cli.utils import determine_root, configure_logging
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)
from facts_experiment_builder.core.experiment.name import InvalidExperimentNameError
from facts_experiment_builder.infra.experiment_storage import (
    FileSystemExperimentStorage,
    ExperimentParentNotFoundError,
    ExperimentRootNotFoundError,
    ExperimentStorageError,
)

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

USER_FACING_ERRORS = (
    InvalidExperimentNameError,
    ExperimentParentNotFoundError,
    ExperimentRootNotFoundError,
    ExperimentStorageError,
    ExperimentAlreadyExistsError,
)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment and parent directory, e.g. experiments/my_first_experiment",
)
@click.option(
    "--climate-step", type=str, required=False, help="Name of the temperature module"
)
@click.option(
    "--supplied-climate-step-data",
    type=click.Path(exists=True),
    required=False,
    help="Path to data to use in place of running a module in the climate step of the experiment.",
)
@click.option(
    "--sealevel-step",
    type=str,
    required=False,
    help="Names of the sea level modules, separated by commas",
)
@click.option(
    "--supplied-totaled-sealevel-step-data",
    type=click.Path(exists=True),
    required=False,
    help="Path to pre-existing totaled sealevel data. Replaces running both the climate and sealevel steps.",
)
@click.option(
    "--total-all-modules",
    type=bool,
    default=True,
    show_default=True,
    help="If true, automatically creates a workflow that includes all specified sealevel modules. User may still choose to specify additional workflows.",
)
@click.option(
    "--extremesealevel-step",
    type=str,
    required=False,
    default=None,
    help="Name of the extreme sea level module (use 'NONE' if no extreme sea level module)",
)
@click.option("--pipeline-id", type=str, required=False, help="Pipeline ID")
@click.option("--scenario", type=str, required=False, help="Scenario")
@click.option("--baseyear", type=int, required=False, help="Base year")
@click.option("--pyear-start", type=int, required=False, help="Projection year start")
@click.option("--pyear-end", type=int, required=False, help="Projection year end")
@click.option("--pyear-step", type=int, required=False, help="Projection year step")
@click.option("--nsamps", type=int, required=False, help="Number of samples")
@click.option(
    "--location-file",
    type=str,
    required=False,
    default="location.lst",
    help="Location file name (Must be in 'shared-input-data' directory).",
)
@click.option(
    "--module-specific-input-data",
    type=str,
    required=False,
    default=None,
    help="Absolute path to module-specific input data to use in experiment.",
)
@click.option(
    "--shared-input-data",
    type=str,
    required=False,
    default=None,
    help="Absolute path to shared input data to use in experiment.",
)
@click.option(
    "--projection-scale",
    type=click.Choice(["global", "local", "both"], case_sensitive=False),
    default="local",
    show_default=True,
    help="Projection scale for this experiment: 'global', 'local', or 'both'.",
)
@click.option(
    "--module-regions",
    type=str,
    multiple=True,
    help=(
        "Specify regions for a module, format: module-name=REGION1,REGION2. "
        "Repeatable. Example: --module-regions emulandice2-glaciers=RGI01,RGI02"
    ),
)
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    default=None,
    show_default=True,
    help="Project root directory, will default to current working directory.",
)
@click.option(
    "--module-registry",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("./facts-module-registry"),
    show_default=True,
    envvar="FEB_MODULE_REGISTRY_DIR",
    help="Path to the facts-module-registry directory to use in experiment setup.",
)
@click.option(
    "--debug", default=False, is_flag=True, help="Enable debug logging globally."
)
@click.option(
    "--debug-target",
    "debug_target",
    default=None,
    help="enable debug logging for a specific module only.",
)
def main(
    experiment_name,
    climate_step,
    supplied_climate_step_data,
    sealevel_step,
    supplied_totaled_sealevel_step_data,
    total_all_modules,
    extremesealevel_step,
    pipeline_id,
    scenario,
    baseyear,
    pyear_start,
    pyear_end,
    pyear_step,
    nsamps,
    location_file,
    module_specific_input_data,
    shared_input_data,
    projection_scale,
    module_regions,
    root,
    debug,
    debug_target,
):
    """Set up a new experiment with setup-experiment CLI command.
    This function includes a number of steps: \n
        - Creates a sub-directory in experiments/ for this experiment. Raises error if one already exists \n
        - Check that all required arguments were received \n
        - If facts-total passed, collects workflows with user prompts

    """

    if debug_target:
        configure_logging(debug_target)
    elif debug:
        configure_logging("all")

    try:
        registry = ModuleRegistry(module_regions)
        root = determine_root(root)
        storage = FileSystemExperimentStorage(root)

        console.rule(
            characters="- - ",
            style="rule",
            title="Initiating setup of a new FACTS experiment",
        )
        console.print(
            "[primary]Step 1:[/primary] Reviewing the information you provided..."
        )
        console.print(
            "[muted] The program will raise an error in step one if the following situations: \n"
            "[muted] - If there is already an experiment matching the provided --experiment-name,[/muted] \n"
            "[muted] - If you do not pass either a module to run, or data to bypass running the module, for a required step,\n"
            "[muted] - If you try to define a workflow that includes a module not present in the sea-level step of the experiment.\n"
        )

        if not sealevel_step and not supplied_totaled_sealevel_step_data:
            console.print(
                "[muted] Note: Skipping sealevel step because no sealevel modules were passed to `setup-new-experiment --sealevel-step`. [/muted]"
            )

        if supplied_totaled_sealevel_step_data:
            console.print(
                "[muted]Note: Totaling step is being skipped because --supplied-totaled-sealevel-step-data was provided.[/muted]"
            )
        prepared_experiment = prepare_experiment_setup(
            storage=storage,
            experiment_name=experiment_name,
            module_regions=module_regions,
            climate_step=climate_step,
            supplied_climate_step_data=supplied_climate_step_data,
            sealevel_step=sealevel_step,
            supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
            extremesealevel_step=extremesealevel_step,
        )
        skeleton = prepared_experiment.experiment_skeleton
        experiment_path = prepared_experiment.experiment_path

        # If framework includes facts-total, collect workflows and attach to skeleton
        sl_modules = skeleton.sealevel_modules
        if is_totaling_needed(sealevel_step=sealevel_step):
            workflow_dict = _collect_workflows(
                complete_modules_list=sl_modules,
                total_all_modules=total_all_modules,
            )
        else:
            workflow_dict = {}
        console.rule(style="rule")
        console.rule(style="rule", title="Setting up new FACTS experiment")
        experiment_spec_data = ExperimentSpecificInputData(
            climate_step_data=supplied_climate_step_data,
            sealevel_step_data=supplied_totaled_sealevel_step_data,
        )
        finalize_experiment_setup(
            experiment_name=experiment_name,
            experiment_path=experiment_path,
            experiment_skeleton=skeleton,
            workflows_dict=workflow_dict,
            pipeline_id=pipeline_id,
            scenario=scenario,
            baseyear=baseyear,
            pyear_end=pyear_end,
            pyear_start=pyear_start,
            pyear_step=pyear_step,
            nsamps=nsamps,
            location_file=location_file,
            module_specific_input_data=module_specific_input_data,
            experiment_specific_input_data=experiment_spec_data,
            shared_input_data=shared_input_data,
            projection_scale=projection_scale,
            registry=registry,
        )

        print_experiment_directory_created(experiment_name, experiment_path)

        print_experiment_modules(experiment_skeleton=skeleton)
        print_experiment_workflows(experiment_skeleton=skeleton)
        # Print what, if any, optional parameters were provided
        print_global_params_info(
            pipeline_id=pipeline_id,
            scenario=scenario,
            baseyear=baseyear,
            pyear_start=pyear_start,
            pyear_end=pyear_end,
            pyear_step=pyear_step,
            nsamps=nsamps,
            location_file=location_file,
            module_specific_input_data=module_specific_input_data,
            shared_input_data=shared_input_data,
        )

        console.rule(style="rule", title="Generating experiment-config.yaml")

        console.print("[primary]Step 5: Writing metadata file using...[/primary]")
        metadata_path = experiment_path / "experiment-config.yaml"

        console.print(
            f"[success]✓ Created experiment-config.yaml at[/success] [secondary]{metadata_path}[/secondary]"
        )

        # Summary
        console.rule(
            style="rule",
            title="[success]✨ Experiment directory setup complete![/success]",
        )
        console.print("\n[primary]Next steps:[/primary]")
        console.print(
            f"  [muted]1.[/muted] Edit [secondary]{metadata_path}[/secondary]"
        )
        console.print(
            "     [muted]Fill in all placeholder values (pipeline-id, scenario, paths, etc.)[/muted]"
        )
        console.print("  [muted]2.[/muted] Generate Docker Compose file.")
    except USER_FACING_ERRORS as e:
        raise click.ClickException(str(e)) from e


def _check_required_experiment_step(
    step_module, step_data, step_module_name, step_data_name
):
    """Function to check that either a module is passed or replacement data is passed for an experiment step."""
    if step_module and step_data:
        raise click.UsageError(
            f"Pass either a module to run during the '{step_module_name}' or data to bypass '{step_data_name}', not both."
        )
    if not step_module and not step_data:
        raise click.UsageError(
            f"Must pass a module to run during '{step_module_name}' or bypass running a module at this step by passing a path to data to '{step_data_name}'. Received neither."
        )


def _check_optional_experiment_step(
    step_module, step_data, step_module_name, step_data_name
):
    """Function to check that either a module is passed or replacement data is passed for an experiment step."""
    if step_module and step_data:
        raise click.UsageError(
            f"Pass either a module to run during the '{step_module_name}' or data to bypass '{step_data_name}', not both."
        )
    if not step_module and not step_data:
        click.echo(
            f"Didn't receive a module to run during '{step_module_name} or data to bypass running that step. You are running an experiment that doesn't include {step_module_name}."
            # Must pass a module to run during '{step_module_name}' or bypass running a module at this step by passing a path to data to '{step_data_name}'. Received neither."
        )


def _check_for_required_args(
    experiment_name,
    climate_step,
    supplied_climate_step_data,
    # sealevel_step,
    supplied_totaled_sealevel_step_data,
):
    if not experiment_name:
        raise click.UsageError(
            "Missing required argument 'experiment_name'. You must pass one with --experiment-name"
        )
    # Climate step is optional when totaled sealevel data is provided (no climate step needed)
    if not supplied_totaled_sealevel_step_data:
        _check_required_experiment_step(
            step_module=climate_step,
            step_data=supplied_climate_step_data,
            step_module_name="--climate-step",
            step_data_name="--supplied-climate-step-data",
        )


def _create_all_modules_workflow(complete_modules_list: list[str]) -> tuple[str, str]:
    workflow_name = "all-modules"
    module_list = complete_modules_list
    module_list_str = unparse_module_list(module_list)
    return (workflow_name, module_list_str)


def _collect_single_workflow(complete_modules_list: list[str]) -> tuple[str, str]:
    workflow_name = click.prompt(
        "Enter a name for this workflow (e.g. wf1)",
        type=str,
    )
    module_list_str = click.prompt(
        "Enter the names of the modules to include in this workflow, separated by commas",
        type=str,
    )
    module_list = parse_module_list_str(module_list_str)
    _validate_modules_list_workflow(module_list, complete_modules_list)
    return (workflow_name, module_list_str)


def _validate_modules_list_workflow(
    workflow_modules: list[str],
    experiment_modules: list[str],
) -> None:
    """Validates the modules listed for a workflow against the modules listed for the experiment."""
    try:
        validate_module_names(workflow_modules, experiment_modules)
    except ValueError as e:
        raise click.UsageError(
            f"{e} \nIt looks like you tried to add a module to a workflow that isn't included in the experiment, please fix this and continue."
        )


def _collect_workflows(
    complete_modules_list: list[str],
    total_all_modules: bool,
) -> dict[str, str]:
    """Collects workflows from the user until they are done."""
    workflow_dict = {}
    if total_all_modules:
        workflow_name, module_list_str = _create_all_modules_workflow(
            complete_modules_list=complete_modules_list,
        )
        workflow_dict[workflow_name] = module_list_str.strip()

        if not click.confirm(
            "Received 'total_all_modules = True'. Do you want to define additional workflows with different combinations of modules?"
        ):
            return workflow_dict
    while True:
        workflow_name, module_list_str = _collect_single_workflow(
            complete_modules_list=complete_modules_list
        )
        workflow_dict[workflow_name] = module_list_str.strip()
        console.print(f"  Workflows so far: [secondary]{workflow_dict}[/secondary]")
        if not click.confirm(
            "Would you like to enter another workflow?", default=False
        ):
            break
    return workflow_dict


def print_experiment_directory_created(experiment_name: str, experiment_path: "Path"):
    console.print(
        "[primary]Step 2:[/primary] Creating experiment directory and sub-directories..."
    )
    console.print(
        f"[bold]  Experiment name:[/bold] [secondary]{experiment_name}[/secondary]"
    )
    console.print(
        f"  ✓ Created experiment directory at: [secondary]{experiment_path}[/secondary]"
    )


def print_experiment_modules(experiment_skeleton: "ExperimentSkeleton"):
    console.print("[muted]  The experiment has the following modules:[/muted]")
    print_climate_step_info(experiment_skeleton)
    print_sealevel_step_info(experiment_skeleton)
    print_extremesealevel_step_info(experiment_skeleton)


def print_experiment_workflows(experiment_skeleton: "ExperimentSkeleton"):
    console.print("[muted]  The experiment has the following workflows: [/muted]")
    print_workflows_info(experiment_skeleton)


def print_climate_step_info(skeleton: "ExperimentSkeleton"):
    value = skeleton.climate_module or skeleton.climate_data
    console.print(f"    - Climate step: [secondary]{value}[/secondary]")


def print_sealevel_step_info(skeleton: "ExperimentSkeleton"):
    value = skeleton.sealevel_modules or skeleton.supplied_totaled_sealevel_step_data
    console.print(f"    - Sea-level step: [secondary]{value}[/secondary]")


def print_extremesealevel_step_info(skeleton: "ExperimentSkeleton"):
    console.print(
        f"    - Extreme sea-level step: [secondary]{skeleton.extremesealevel_module}[/secondary]"
    )


def print_workflows_info(skeleton: "ExperimentSkeleton"):
    console.print(f"    - Experiment workflows: [secondary]{skeleton.workflows}")


def print_global_params_info(
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
):
    """Prints some CLI info about the global parameters provided."""
    # Print some CLI info
    if any(
        [
            pipeline_id,
            scenario,
            baseyear,
            pyear_start,
            pyear_end,
            pyear_step,
            nsamps,
            location_file,
            module_specific_input_data,
            shared_input_data,
        ]
    ):
        console.print(
            "[muted]  CLI arguments provided will be included in experiment-config.yaml[/muted]"
        )


if __name__ == "__main__":
    main()
