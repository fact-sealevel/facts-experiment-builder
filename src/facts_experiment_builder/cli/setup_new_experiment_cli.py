"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_new_experiment.py.

"""

import click
import logging
from pathlib import Path
from facts_experiment_builder.application.setup_new_experiment import (
    setup_new_experiment_fs,
    init_new_experiment,
    populate_experiment_defaults,
)
from facts_experiment_builder.infra.write_experiment_metadata import (
    write_metadata_yaml_jinja2,
) #TODO move this eventually
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment"
)
@click.option("--temperature-module",
    type=str,
    required=True,
    help="Name of the temperature module (use 'NONE' if no temperature module)"
)
@click.option("--sealevel-modules",
    type=str,
    required=True,
    help="Names of the sea level modules, separated by commas"
)
@click.option("--framework-modules",
    type=str,
    required=False,
    default= None,
    help="Names of the framework modules, separated by commas"
)
@click.option("--extremesealevel-module",
    type=str,
    required=False,
    default= None,
    help="Name of the extreme sea level module (use 'NONE' if no extreme sea level module)"
)
@click.option("--pipeline-id",
    type=str,
    required=False,
    help="Pipeline ID"
)
@click.option("--scenario",
    type=str,
    required=False,
    help="Scenario"
)
@click.option("--baseyear",
    type=int,
    required=False,
    help="Base year"
)
@click.option("--pyear-start",
    type=int,
    required=False,
    help="Projection year start"
)
@click.option("--pyear-end",
    type=int,
    required=False,
    help="Projection year end"
)
@click.option("--pyear-step",
    type=int,
    required=False,
    help="Projection year step"
)
@click.option("--nsamps",
    type=int,
    required=False,
    help="Number of samples"
)
@click.option("--seed",
    type=int,
    required=False,
    help="Random seed to use for sampling"
)
@click.option("--location-file",
    type=str,
    required=False,
    default="location.lst",
    help="Location file name"
)
@click.option("--fingerprint-dir",
    type=str,
    required=False,
    help="Name of directory holding GRD fingerprint data",
    default="FPRINT"
)
def main(
    experiment_name, 
    temperature_module, 
    sealevel_modules,
    framework_modules,
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
):
    """Create a new experiment directory with template files using Jinja2 templating.
    """

    # Parse comma-separated sealevel modules into a list
    sealevel_modules_list = [m.strip() for m in sealevel_modules.split(',') if m.strip()]
    
    # Step 1: Create experiment directory and sub-directories
    click.echo("Step 1: Creating experiment directory and sub-directories...")
    module_names = [temperature_module] + sealevel_modules_list

    experiment_path =setup_new_experiment_fs(experiment_name=experiment_name, module_names=module_names)
    
    # Print some setup info
    exp_setup_message = f"Setting up new experiment: {experiment_name}"
    click.echo(exp_setup_message)
    temp_module_message = f"  Temperature module: {temperature_module}"
    click.echo(temp_module_message)
    sealevel_modules_message = f"  Sea level modules: {sealevel_modules_list}"
    click.echo(sealevel_modules_message)
    framework_modules_message = f"  Framework modules: {framework_modules}"
    click.echo(framework_modules_message)
    extremesealevel_module_message = f"  Extreme sea level module: {extremesealevel_module}"
    click.echo(extremesealevel_module_message)

    # Print some CLI info
    if any([pipeline_id, scenario, baseyear, pyear_start, pyear_end, pyear_step, nsamps, seed]):
        click.echo("  CLI arguments provided - will be included in metadata")
    click.echo("\n" + "="*70)
    
   
    # Step 2: Create FactsExperiment from template (FactsExperiment-centric flow)
    click.echo("Step 2: Generating metadata template...")
    experiment = init_new_experiment(
        experiment_name=experiment_name,
        temperature_module=temperature_module,
        sealevel_modules=sealevel_modules_list,
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
    )
    
    # Step 3: Populate experiment with defaults from defaults.yml files
    # Revert: for module_name in ...: metadata = populate_metadata_with_defaults(metadata, module_name)
    click.echo("Step 3: Populating metadata with defaults from defaults.yml files...")
    for module_name in [temperature_module] + sealevel_modules_list:
        if module_name and module_name.upper() != "NONE":
            modules_message = f"  Populating defaults for module: {module_name}"
            click.echo(modules_message)
            populate_experiment_defaults(experiment, module_name)
    
    # Step 5: Write metadata using Jinja2 templating (accepts FactsExperiment or dict)
    click.echo("Step 4: Writing metadata file using Jinja2 templating...")
    metadata_path = experiment_path / "experiment-metadata.yml"
    write_metadata_yaml_jinja2(experiment, metadata_path)
    click.echo(f"✓ Created experiment-metadata.yml at {metadata_path}")
    
    # Summary
    format_message = "\n" + "="*70
    click.echo(format_message)
    dir_setup_complete_message = "✨ Experiment directory setup complete!"
    click.echo(dir_setup_complete_message)
    next_steps_message = "\nNext steps:"
    click.echo(next_steps_message)
    edit_metadata_message = f"  1. Edit {metadata_path}"
    click.echo(edit_metadata_message)
    fill_in_placeholders_message = "     - Fill in all placeholder values (pipeline-id, scenario, paths, etc.)"
    click.echo(fill_in_placeholders_message)
    generate_compose_message = f"  2. Generate Docker Compose:"
    click.echo(generate_compose_message)
    run_compose_message = f"     uv run generate-compose {experiment_path}"
    click.echo(run_compose_message)

if __name__ == "__main__":
    main()
