"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_new_experiment.py.

"""

import click
from pathlib import Path
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.setup_new_experiment import (
    setup_new_experiment_fs,
    init_new_experiment,
    populate_experiment_defaults,
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
    "--temperature-module",
    type=str,
    required=True,
    help="Name of the temperature module (use 'NONE' if no temperature module)",
)
@click.option(
    "--sealevel-modules",
    type=str,
    required=True,
    help="Names of the sea level modules, separated by commas",
)
@click.option(
    "--framework-module",
    type=str,
    required=False,
    default=None,
    help="Name of the framework module (use 'NONE' if no framework module)",
)
@click.option(
    "--extremesealevel-module",
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
    temperature_module,
    sealevel_modules,
    framework_module,
    extremesealevel_module,
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
    """Create a new experiment directory with template files using Jinja2 templating."""
    # Parse comma-separated module names into a list
    (
        temperature_module_list,
        sealevel_modules_list,
        framework_modules_list,
        extremesealevel_module_list,
    ) = _parse_modules_list(
        temperature_module,
        sealevel_modules,
        framework_module,
        extremesealevel_module,
    )
    # Combine into a total list of all modules in the experiment
    total_modules_list = (
        temperature_module_list
        + sealevel_modules_list
        + framework_modules_list
        + extremesealevel_module_list
    )

    # If framework includes facts-total, collect workflows interactively
    if framework_modules_list and "facts-total" in framework_modules_list:
        workflow_dict = _collect_workflows(total_modules_list)
    else:
        workflow_dict = {}
    console.rule(style="rule")
    console.rule(style="rule", title="Setting up new FACTS experiment")
    console.print(
        "[primary]Step 1:[/primary] Reviewing the information you provided and making sure everything looks okay..."
    )

    # Validate the total list of modules
    _validate_modules_list_experiment(total_modules_list)

    # Step 2: Create experiment directory and sub-directories
    experiment_path = setup_new_experiment_fs(
        experiment_name=experiment_name, module_names=total_modules_list
    )
    # Print step 2 info
    print_step2_info(
        experiment_name=experiment_name,
        temperature_module_list=temperature_module_list,
        sealevel_modules_list=sealevel_modules_list,
        framework_modules_list=framework_modules_list,
        extremesealevel_module_list=extremesealevel_module_list,
        experiment_path=experiment_path,
    )
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

    experiment = init_new_experiment(
        experiment_name=experiment_name,
        temperature_module=temperature_module,
        sealevel_modules=sealevel_modules_list,
        framework_modules=framework_modules_list,
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
        module_specific_inputs=module_specific_inputs,
        general_inputs=general_inputs,
    )

    # Step 3: Populate experiment with defaults from defaults.yml files
    # Revert: for module_name in ...: metadata = populate_metadata_with_defaults(metadata, module_name)
    console.print(
        "[primary]Step 4: Populating metadata with defaults from defaults.yml files...[/primary]"
    )
    for module_name in (
        [temperature_module]
        + sealevel_modules_list
        + [framework_module]
        + extremesealevel_module_list
    ):
        if module_name and module_name.upper() != "NONE":
            console.print(
                f"  Populating defaults for module: [secondary]{module_name}[/secondary]"
            )
            populate_experiment_defaults(experiment, module_name)

    # Step 4: Write metadata using Jinja2 templating (accepts FactsExperiment or dict)
    console.print(
        "[primary]Step 5: Writing metadata file using Jinja2 templating...[/primary]"
    )
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


def _parse_modules_list(
    temperature_module: str,
    sealevel_modules: str,
    framework_module: str,
    extremesealevel_module: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Parse the module list strings and return them as lists."""
    return (
        parse_module_list(temperature_module),
        parse_module_list(sealevel_modules),
        parse_module_list(framework_module),
        parse_module_list(extremesealevel_module),
    )


def _collect_single_workflow(total_modules_list: list[str]) -> tuple[str, str]:
    workflow_name = click.prompt(
        "Enter a name for this workflow (e.g. wf1)",
        type=str,
    )
    module_list_str = click.prompt(
        "Enter the names of the modules to include in this workflow, separated by commas",
        type=str,
    )
    module_list = parse_module_list(module_list_str)
    _validate_modules_list_workflow(module_list, total_modules_list)
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


def _collect_workflows(total_modules_list: list[str]) -> dict[str, str]:
    """Collects workflows from the user until they are done."""
    workflow_dict = {}
    while True:
        workflow_name, module_list_str = _collect_single_workflow(total_modules_list)
        workflow_dict[workflow_name] = module_list_str.strip()
        console.print(f"  Workflows so far: [secondary]{workflow_dict}[/secondary]")
        if not click.confirm(
            "Would you like to enter another workflow?", default=False
        ):
            break
    return workflow_dict


def print_step2_info(
    experiment_name: str,
    temperature_module_list: list[str],
    sealevel_modules_list: list[str],
    framework_modules_list: list[str],
    extremesealevel_module_list: list[str],
    experiment_path: Path,
):
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
    # Print some setup info
    console.print(
        f"    - Temperature module: [secondary]{temperature_module_list}[/secondary]"
    )
    console.print(
        f"    - Sea level modules: [secondary]{sealevel_modules_list}[/secondary]"
    )
    console.print(
        f"    - Framework modules: [secondary]{framework_modules_list}[/secondary]"
    )
    console.print(
        f"    - Extreme sea level module: [secondary]{extremesealevel_module_list}[/secondary]"
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
