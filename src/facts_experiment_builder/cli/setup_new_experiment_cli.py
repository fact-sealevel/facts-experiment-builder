"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_new_experiment.py.

"""

import click
from rich.console import Console
from rich.theme import Theme
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

# Mid-range lapaz stops — visible on both light and dark terminals
# Avoids the near-black (#190B35) and near-white (#F9F3C5) extremes
lapaz_theme = Theme({
    "primary":   "bold #1E6896",   # lapaz_25 — royal blue, high contrast on both
    "secondary": "#228B8D",        # lapaz_50 — teal, solid mid-tone
    "accent":    "#5AADA8",        # lapaz_40ish — slightly lighter teal
    "success":   "#82C8A0",        # lapaz_75 — sage green, readable on dark/mid BGs
    "muted":     "#4A7FA5",        # slightly desaturated blue — safe mid-tone
    "rule":      "#228B8D",        # teal rule lines
    "warning":   "bold #C4A862",   # warm gold — visible on both (not in lapaz but complements it)
    "danger":    "bold #C0504A",   # muted red — universal danger signal
})

console = Console(theme=lapaz_theme)


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
    console.rule(style="rule", title="Setting up new FACTS experiment")
    console.print("[primary]Step 1:[/primary] I'm reading the information you provided and making sure everything looks okay...")

    # Parse comma-separated module names into a list
    temperature_module_list, sealevel_modules_list, framework_modules_list, extremesealevel_module_list = _parse_modules_list(
        temperature_module,
        sealevel_modules,
        framework_module,
        extremesealevel_module,
    )
    # Combine into a total list of all modules in the experiment
    total_modules_list = temperature_module_list + sealevel_modules_list + framework_modules_list + extremesealevel_module_list

    # Validate the total list of modules
    _validate_modules_list(total_modules_list)

    # If framework includes facts-total, collect workflows interactively
    if framework_modules_list and "facts-total" in framework_modules_list:
        workflow_dict = _collect_workflows()
    else:
        workflow_dict = {}

    # Step 2: Create experiment directory and sub-directories
    console.print("[primary]Step 2:[/primary] Creating experiment directory and sub-directories...")

    experiment_path = setup_new_experiment_fs(
        experiment_name=experiment_name, module_names=total_modules_list
    )

    console.print(f"[bold]     Setting up new experiment:[/bold] [secondary]{experiment_name}[/secondary]")

    console.print(f"     ✓ Created experiment directory at: [secondary]{experiment_path}[/secondary]")
    console.print("[muted]-The experiment has the following modules:[/muted]")
    # Print some setup info
    console.print(f"    - Temperature module: [secondary]{temperature_module_list}[/secondary]")
    console.print(f"    - Sea level modules: [secondary]{sealevel_modules_list}[/secondary]")
    console.print(f"    - Framework modules: [secondary]{framework_modules_list}[/secondary]")
    console.print(f"    - Extreme sea level module: [secondary]{extremesealevel_module_list}[/secondary]")



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
        ]
    ):
        console.print("[muted]-CLI arguments provided will be included in metadata[/muted]")
    console.rule(style="rule")

    # Step 2: Create FactsExperiment from template
    console.print("[primary]Step 3: Generating metadata template...[/primary]")
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
    console.print("[primary]Step 4: Populating metadata with defaults from defaults.yml files...[/primary]")
    for module_name in (
        [temperature_module]
        + sealevel_modules_list
        + [framework_module]
        + extremesealevel_module_list
    ):
        if module_name and module_name.upper() != "NONE":
            console.print(f"  Populating defaults for module: [secondary]{module_name}[/secondary]")
            populate_experiment_defaults(experiment, module_name)

    # Step 4: Write metadata using Jinja2 templating (accepts FactsExperiment or dict)
    console.print("[primary]Step 5: Writing metadata file using Jinja2 templating...[/primary]")
    metadata_path = experiment_path / "experiment-metadata.yml"
    write_metadata_yaml_jinja2(experiment, metadata_path)
    console.print(f"[success]✓ Created experiment-metadata.yml at[/success] [secondary]{metadata_path}[/secondary]")

    # Summary
    console.rule(style="rule")
    console.print("[success]✨ Experiment directory setup complete![/success]")
    console.print("\n[primary]Next steps:[/primary]")
    console.print(f"  [muted]1.[/muted] Edit [secondary]{metadata_path}[/secondary]")
    console.print("     [muted]Fill in all placeholder values (pipeline-id, scenario, paths, etc.)[/muted]")
    console.print("  [muted]2.[/muted] Generate Docker Compose:")
    console.print(f"     [accent]uv run generate-compose {experiment_path}[/accent]")

def _parse_modules_list(
        temperature_module: str,
        sealevel_modules: str,
        framework_module: str,
        extremesealevel_module: str,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Parse the module lists strings and return them as lists"""
        temperature_module_list = parse_module_list(temperature_module)
        sealevel_modules_list = parse_module_list(sealevel_modules)
        framework_modules_list = parse_module_list(framework_module)
        extremesealevel_module_list = parse_module_list(extremesealevel_module)
        return (
            temperature_module_list, 
            sealevel_modules_list, 
            framework_modules_list, 
            extremesealevel_module_list
        )

def _validate_modules_list(
        modules_list: list[str],
    ) -> None:

        valid_module_names = ModuleRegistry.default().list_modules()
        try:
            validate_module_names(modules_list, valid_module_names)
        except ValueError as e:
            raise click.UsageError(
                f"{e}\nIt looks like an invalid module name was passed to setup-new-experiment. \nThe modules passed are {modules_list}. \nCheck if you made a typo or if the module is available in the registry (try running 'uv run list-modules')."
            )

def _collect_workflows() -> dict[str, str]:
        workflow_dict = {}
        first = True
        while True:
            if first:
                workflow_name = click.prompt(
                    "Enter a name for your first workflow, ex. wf1",
                    type=str,
                    default="wf1",
                )
                first = False
            else:
                workflow_name = click.prompt(
                    "Enter a name for this workflow",
                    type=str,
                )
                workflow_name = workflow_name.strip() or "wf"
                module_list_str = click.prompt(
                    "Enter the names of the modules to include in this workflow. "
                    "Modules should be separated by commas with no spaces between words",
                    type=str,
                )
                workflow_dict[workflow_name] = module_list_str.strip()
                if not click.confirm(
                    "Would you like to enter another workflow?",
                    default=False,
                ):
                    break
            console.print(f"  Workflows: [secondary]{workflow_dict}[/secondary]")
        return workflow_dict

if __name__ == "__main__":
    main()
