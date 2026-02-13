"""Alternate CLI for setting up new experiments using Jinja2 templating.

This is an alternative to setup_new_experiment_cli.py that explicitly uses
the Jinja2-based YAML generation from setup_new_experiment_jinja2.py.

The main difference is that this CLI directly calls write_metadata_yaml_jinja2()
and shows the Jinja2 workflow more explicitly.
"""

import click
import logging
from pathlib import Path
from facts_experiment_builder.utils.setup_new_experiment import (
    write_metadata_yaml_jinja2,
    generate_metadata_template,
    populate_metadata_with_defaults,
    create_experiment_directory,
    create_experiment_directory_files,
)

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
def main(
    experiment_name, 
    temperature_module, 
    sealevel_modules,
    pipeline_id,
    scenario,
    baseyear,
    pyear_start,
    pyear_end,
    pyear_step,
    nsamps,
    seed,
):
    """Create a new experiment directory with template files using Jinja2 templating.
    
    This command uses the Jinja2-based YAML generation system, which provides
    more declarative template-based metadata file generation.
    """
    # Parse comma-separated sealevel modules into a list
    sealevel_modules_list = [m.strip() for m in sealevel_modules.split(',') if m.strip()]
    
    logger.info(f"Setting up new experiment (Jinja2): {experiment_name}")
    logger.info(f"  Temperature module: {temperature_module}")
    logger.info(f"  Sea level modules: {sealevel_modules_list}")
    if any([pipeline_id, scenario, baseyear, pyear_start, pyear_end, pyear_step, nsamps, seed]):
        logger.info("  CLI arguments provided - will be included in metadata")
    
    # Step 1: Create experiment directory
    logger.info("Step 1: Creating experiment directory...")
    experiment_path = create_experiment_directory(experiment_name=experiment_name)
    
    # Step 2: Setup data directory structure and README file
    logger.info("Step 2: Creating data directories and README...")
    create_experiment_directory_files(experiment_path=experiment_path)
    
    # Step 3: Generate metadata template
    logger.info("Step 3: Generating metadata template...")
    metadata = generate_metadata_template(
        experiment_name=experiment_name,
        temperature_module=temperature_module,
        sealevel_modules=sealevel_modules_list,
        experiment_path=experiment_path,
        pipeline_id=pipeline_id,
        scenario=scenario,
        baseyear=baseyear,
        pyear_start=pyear_start,
        pyear_end=pyear_end,
        pyear_step=pyear_step,
        nsamps=nsamps,
        seed=seed,
    )
    
    # Step 4: Populate metadata with defaults from defaults.yml files
    logger.info("Step 4: Populating metadata with defaults from defaults.yml files...")
    for module_name in [temperature_module] + sealevel_modules_list:
        if module_name and module_name.upper() != "NONE":
            logger.info(f"  Populating defaults for module: {module_name}")
            metadata = populate_metadata_with_defaults(metadata, module_name)
    
    # Step 5: Write metadata using Jinja2 templating
    logger.info("Step 5: Writing metadata file using Jinja2 templating...")
    metadata_path = experiment_path / "experiment-metadata.yml"
    write_metadata_yaml_jinja2(metadata, metadata_path)
    logger.info(f"✓ Created experiment-metadata.yml at {metadata_path}")
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("✨ Experiment directory setup complete!")
    logger.info("\nNext steps:")
    logger.info(f"  1. Edit {metadata_path}")
    logger.info("     - Fill in all placeholder values (pipeline-id, scenario, paths, etc.)")
    logger.info(f"  2. Generate Docker Compose:")
    logger.info(f"     uv run generate-compose {experiment_path}")


if __name__ == "__main__":
    main()
