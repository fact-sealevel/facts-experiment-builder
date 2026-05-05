"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_experiment.py.

"""

import dataclasses
import click
from pathlib import Path
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.setup_experiment import (
    setup_experiment_fs,
    experiment_skeleton_to_facts_experiment,
    populate_experiment_directory,
)
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    ExperimentSkeleton,
)
from facts_experiment_builder.infra.write_experiment_metadata import (
    write_metadata_yaml_jinja2,
)  # TODO move this eventually
from facts_experiment_builder.core.registry import ModuleRegistry
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list,
    unparse_module_list,
    validate_module_names,
)
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name", type=str, required=True, help="Name of the experiment"
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
@click.option("--debug/--no-debug", default=False)
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
    debug,
):
    """Set up a new experiment with setup-new-experiment CLI command.
    This function includes a number of steps: \n
        - Creates a sub-directory in experiments/ for this experiment. Raises error if one already exists \n
        - Check that all required arguments were Received \n
        - Create a SkeletonExperiment object. This only includes information about which modules will be included in the experiment. \n
        - If facts-total passed, collects workflows w/ user prompts

    """
    if debug:
        logging.root.setLevel(logging.INFO)

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
    # first, check that experiment doesn't already exist
    try:
        experiment_path = setup_experiment_fs(experiment_name=experiment_name)
    except ExperimentAlreadyExistsError as e:
        raise click.UsageError(str(e))

    # Build the skeleton from CLI inputs (parses comma-separated strings, no YAML loading)
    try:
        skeleton = ExperimentSkeleton.from_cli_inputs(
            climate_step=climate_step,
            supplied_climate_step_data=supplied_climate_step_data,
            sealevel_step=sealevel_step,
            supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
            extremesealevel_step=extremesealevel_step,
        )
    except ValueError as e:
        raise click.UsageError(
            "Failed to create experient skeleton in application.setup_experiment: %s",
            str(e),
        )

    # If no sealevel modules are provided, skip sealevel step
    if not skeleton.sealevel_modules:
        console.print(
            "[muted] Note: Skipping sealevel step because no sealevel modules were passed to `setup-new-experiment --sealevel-step`. [/muted]"
        )

    if supplied_totaled_sealevel_step_data:
        console.print(
            "[muted]Note: Totaling step is being skipped because --supplied-totaled-sealevel-step-data was provided.[/muted]"
        )

    # If framework includes facts-total, collect workflows and attach to skeleton
    sl_modules = skeleton.sealevel_modules
    if skeleton.totaling_module == "facts-total":
        workflow_dict = _collect_workflows(
            complete_modules_list=sl_modules,
            total_all_modules=total_all_modules,
        )
        skeleton = dataclasses.replace(skeleton, workflows=workflow_dict)
    console.rule(style="rule")
    console.rule(style="rule", title="Setting up new FACTS experiment")

    # Create output dir etc.
    populate_experiment_directory(
        experiment_path=experiment_path, module_names=skeleton.all_module_names
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

    # Step 2: Create FactsExperiment from template

    experiment = experiment_skeleton_to_facts_experiment(
        experiment_name=experiment_name,
        skeleton=skeleton,
        pipeline_id=pipeline_id,
        scenario=scenario,
        baseyear=baseyear,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        nsamps=nsamps,
        location_file=location_file,
        module_specific_input_data=module_specific_input_data,
        experiment_specific_input_data=supplied_climate_step_data,
        shared_input_data=shared_input_data,
    )

    # Step 4: Write metadata using Jinja2 templating (accepts FactsExperiment or dict)
    console.print("[primary]Step 5: Writing metadata file using...[/primary]")
    metadata_path = experiment_path / "experiment-config.yaml"
    registry_version = ModuleRegistry.default().get_version()
    write_metadata_yaml_jinja2(
        experiment, metadata_path, module_registry_version=registry_version
    )
    console.print(
        f"[success]✓ Created experiment-config.yaml at[/success] [secondary]{metadata_path}[/secondary]"
    )

    # Summary
    console.rule(
        style="rule", title="[success]✨ Experiment directory setup complete![/success]"
    )
    console.print("\n[primary]Next steps:[/primary]")
    console.print(f"  [muted]1.[/muted] Edit [secondary]{metadata_path}[/secondary]")
    console.print(
        "     [muted]Fill in all placeholder values (pipeline-id, scenario, paths, etc.)[/muted]"
    )
    console.print("  [muted]2.[/muted] Generate Docker Compose file.")


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
    module_list = parse_module_list(module_list_str)
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


def print_experiment_modules(experiment_skeleton: ExperimentSkeleton):
    console.print("[muted]  The experiment has the following modules:[/muted]")
    print_climate_step_info(experiment_skeleton)
    print_sealevel_step_info(experiment_skeleton)
    print_extremesealevel_step_info(experiment_skeleton)


def print_experiment_workflows(experiment_skeleton: ExperimentSkeleton):
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
