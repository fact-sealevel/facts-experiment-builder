"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_new_experiment.py.

"""

import dataclasses
import click
from pathlib import Path
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.setup_new_experiment import (
    setup_new_experiment_fs,
    experimentSkeleton_to_factsExperiment,
    populate_experiment_defaults,
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
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list,
    validate_module_names,
)
from facts_experiment_builder.core.registry import ModuleRegistry


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name", type=str, required=True, help="Name of the experiment"
)
@click.option(
    "--climate-step", type=str, required=False, help="Name of the temperature module"
)
@click.option(
    "--climate-step-data",
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
    "--sealevel-step-data",
    type=click.Path(exists=True),
    required=False,
    help="Path to data to use in place of running modules in sea-level step",
)
@click.option(
    "--totaling-step",
    type=str,
    default="facts-total",
    show_default=True,
    help="Name of the totaling step module (use 'NONE' if you do not want to call the totaling module)",
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
    "--seed", type=int, required=False, help="Random seed to use for sampling"
)
@click.option(
    "--location-file",
    type=str,
    required=False,
    default="location.lst",
    help="Location file name",
)
@click.option(
    "--fingerprint-dir",
    type=str,
    required=False,
    help="Name of directory holding GRD fingerprint data",
    default="FPRINT",
)
@click.option(
    "--module-specific-inputs",
    type=str,
    required=False,
    default=None,
    help="Path to module-specific input data (written to experiment metadata)",
)
@click.option(
    "--general-inputs",
    type=str,
    required=False,
    default=None,
    help="Path to general input data (written to experiment metadata)",
)
def main(
    experiment_name,
    climate_step,
    climate_step_data,
    sealevel_step,
    sealevel_step_data,
    totaling_step,
    extremesealevel_step,
    pipeline_id,
    scenario,
    baseyear,
    pyear_start,
    pyear_end,
    pyear_step,
    nsamps,
    seed,
    location_file,
    fingerprint_dir,
    module_specific_inputs,
    general_inputs,
):
    """Set up a new experiment with setup-new-experiment CLI command.
    This function includes a number of steps:
        - Creates a sub-directory in experiments/ for this experiment. Raises error if one already exists
        - Check that all required arguments were Received
        - Create a SkeletonExperiment object. This only includes information about which modules will be included in the experiment.
        - If facts-total passed, collects workflows w/ user prompts

    """
    # first, check that experiment doesn't already exist
    try:
        experiment_path = setup_new_experiment_fs(experiment_name=experiment_name)
    except ExperimentAlreadyExistsError as e:
        raise click.UsageError(str(e))
    # second, check that all required arguments are present.
    _check_for_required_args(
        experiment_name=experiment_name,
        climate_step=climate_step,
        climate_step_data=climate_step_data,
        sealevel_step=sealevel_step,
        sealevel_step_data=sealevel_step_data,
    )

    # Build the skeleton from CLI inputs (parses comma-separated strings, no YAML loading)
    skeleton = ExperimentSkeleton.from_cli_inputs(
        climate_step=climate_step,
        climate_step_data=climate_step_data,
        sealevel_step=sealevel_step,
        sealevel_step_data=sealevel_step_data,
        totaling_step=totaling_step,
        extremesealevel_step=extremesealevel_step,
    )

    # If sealevel data is provided, totaling cannot run (no sealevel outputs to total)
    if (
        skeleton.sealevel_data
        and skeleton.totaling_module
        and skeleton.totaling_module.upper() != "NONE"
    ):
        console.print(
            "[muted]Note: Totaling step is being skipped because --sealevel-step-data was provided.[/muted]"
        )
        skeleton = dataclasses.replace(skeleton, totaling_module=None)

    # Validate the total list of modules
    _validate_modules_list_experiment(skeleton.all_module_names)

    # If framework includes facts-total, collect workflows and attach to skeleton
    if skeleton.totaling_module == "facts-total":
        workflow_dict = _collect_workflows(skeleton.all_module_names)
        skeleton = dataclasses.replace(skeleton, workflows=workflow_dict)
    console.rule(style="rule")
    console.rule(style="rule", title="Setting up new FACTS experiment")
    console.print(
        "[primary]Step 1:[/primary] Reviewing the information you provided and making sure everything looks okay..."
    )

    # Create output dir etc.
    populate_experiment_directory(
        experiment_path=experiment_path, module_names=skeleton.all_module_names
    )
    print_experiment_directory_created(experiment_name, experiment_path)
    print_climate_step_info(skeleton)
    print_sealevel_step_info(skeleton)
    print_totaling_step_info(skeleton)
    print_extremesealevel_step_info(skeleton)
    # Print what, if any, optional parameters were provided
    print_global_params_info(
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
        module_specific_inputs=module_specific_inputs,
        general_inputs=general_inputs,
    )

    console.rule(style="rule", title="Generating experiment-metadata.yml")

    # Step 2: Create FactsExperiment from template

    experiment = experimentSkeleton_to_factsExperiment(
        experiment_name=experiment_name,
        skeleton=skeleton,
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
        module_specific_inputs=module_specific_inputs,
        experiment_specific_inputs=climate_step_data,
        general_inputs=general_inputs,
    )

    # Step 3: Populate experiment with defaults from defaults.yml files
    # Revert: for module_name in ...: metadata = populate_metadata_with_defaults(metadata, module_name)
    console.print(
        "[primary]Step 4: Populating metadata with defaults from defaults.yml files...[/primary]"
    )
    for module_name in skeleton.all_module_names:
        if module_name and module_name.upper() != "NONE":
            console.print(
                f"  Populating defaults for module: [secondary]{module_name}[/secondary]"
            )
            populate_experiment_defaults(experiment, module_name)

    # Step 4: Write metadata using Jinja2 templating (accepts FactsExperiment or dict)
    console.print("[primary]Step 5: Writing metadata file using...[/primary]")
    metadata_path = experiment_path / "experiment-metadata.yml"
    write_metadata_yaml_jinja2(experiment, metadata_path)
    console.print(
        f"[success]✓ Created experiment-metadata.yml at[/success] [secondary]{metadata_path}[/secondary]"
    )

    # Summary
    console.rule(
        style="rule", title="[success]✨ Experiment directory setup complete![/success]"
    )
    # console.print("[success]✨ Experiment directory setup complete![/success]")
    console.print("\n[primary]Next steps:[/primary]")
    console.print(f"  [muted]1.[/muted] Edit [secondary]{metadata_path}[/secondary]")
    console.print(
        "     [muted]Fill in all placeholder values (pipeline-id, scenario, paths, etc.)[/muted]"
    )
    console.print("  [muted]2.[/muted] Generate Docker Compose:")
    console.print(f"     [accent]uv run generate-compose {experiment_path}[/accent]")


def _check_experiment_step(step_module, step_data, step_module_name, step_data_name):
    """Function to check that either a module is passed or replacement data is passed for an experiment step."""
    if step_module and step_data:
        raise click.UsageError(
            f"Pass either '{step_module_name}' or '{step_data_name}', not both."
        )
    if not step_module and not step_data:
        raise click.UsageError(
            f"Must pass one of '{step_module_name}' or '{step_data_name}'. Received neither."
        )


def _check_for_required_args(
    experiment_name,
    climate_step,
    climate_step_data,
    sealevel_step,
    sealevel_step_data,
):
    if not experiment_name:
        raise click.UsageError(
            "Missing required argument 'experiment_name'. You must pass one with --experiment-name"
        )
    # Check climate step
    _check_experiment_step(
        climate_step, climate_step_data, "--climate-step", "--climate-step-data"
    )
    # Check sealevel step
    _check_experiment_step(
        sealevel_step, sealevel_step_data, "--sealevel-step", "--sealevel-step-data"
    )


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


def _validate_modules_list_experiment(
    modules_list: list[str],
) -> None:
    """Validates the modules listed for an experiment against the modules in the module registry."""
    valid_module_names = ModuleRegistry.default().list_modules()
    try:
        validate_module_names(modules_list, valid_module_names)
    except ValueError as e:
        raise click.UsageError(
            f"{e}\nIt looks like an invalid module name was passed to setup-new-experiment. \nThe modules passed are {modules_list}. \nCheck if you made a typo or if the module is available in the registry (try running 'uv run list-modules')."
        )


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


def _collect_workflows(complete_modules_list: list[str]) -> dict[str, str]:
    """Collects workflows from the user until they are done."""
    workflow_dict = {}
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
        f"[bold]  Setting up new experiment:[/bold] [secondary]{experiment_name}[/secondary]"
    )
    console.print(
        f"  ✓ Created experiment directory at: [secondary]{experiment_path}[/secondary]"
    )
    console.print("[muted]  The experiment has the following modules:[/muted]")


def print_climate_step_info(skeleton: "ExperimentSkeleton"):
    value = skeleton.climate_module or skeleton.climate_data
    console.print(f"    - Climate step: [secondary]{value}[/secondary]")


def print_sealevel_step_info(skeleton: "ExperimentSkeleton"):
    value = skeleton.sealevel_modules or skeleton.sealevel_data
    console.print(f"    - Sea level step: [secondary]{value}[/secondary]")


def print_totaling_step_info(skeleton: "ExperimentSkeleton"):
    console.print(
        f"    - Totaling step: [secondary]{skeleton.totaling_module}[/secondary]"
    )


def print_extremesealevel_step_info(skeleton: "ExperimentSkeleton"):
    console.print(
        f"    - Extreme sea level step: [secondary]{skeleton.extremesealevel_module}[/secondary]"
    )


def print_global_params_info(
    pipeline_id: str,
    scenario: str,
    baseyear: int,
    pyear_start: int,
    pyear_end: int,
    pyear_step: int,
    nsamps: int,
    seed: int,
    location_file: str,
    fingerprint_dir: str,
    module_specific_inputs: str,
    general_inputs: str,
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
            seed,
            location_file,
            fingerprint_dir,
            module_specific_inputs,
            general_inputs,
        ]
    ):
        console.print(
            "[muted]-CLI arguments provided will be included in metadata[/muted]"
        )


if __name__ == "__main__":
    main()
