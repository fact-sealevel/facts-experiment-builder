"""CLI for setting up new experiments using Jinja2 templating.

This script uses Jinja2-based YAML generation from setup_experiment.py.
"""

from pathlib import Path
import click
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.core.experiment.experiment_skeleton import (
    is_totaling_needed,
)
from pydantic import ValidationError
from facts_experiment_builder.application.setup_experiment import (
    prepare_experiment_setup,
    finalize_experiment_setup,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from facts_experiment_builder.core.experiment.experiment_skeleton import (
        ExperimentSkeleton,
    )
from facts_experiment_builder.core.experiment.module_name_validation import (
    validate_module_names,
)
from facts_experiment_builder.cli.workflow_prompts import (
    _collect_workflows,
)
from facts_experiment_builder.cli.utils import configure_logging
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
)

from facts_experiment_builder.core.experiment.name import InvalidExperimentNameError
from facts_experiment_builder.io.experiment_storage import (
    FileSystemExperimentStorage,
    ExperimentParentNotFoundError,
    ExperimentRootNotFoundError,
    ExperimentStorageError,
)
from facts_experiment_builder.io.module_registry import FileSystemModuleRegistry

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
    help="Name of the experiment and parent directory, e.g. experiments/my_first_experiment. This is used in conjunction with `--workspace-dir` (by default, present working directory) to create an experiment directory that holds config files and output data associated with the experiment.",
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
    "--workspace-dir",
    type=click.Path(
        path_type=Path, exists=True, dir_okay=True, file_okay=False, resolve_path=True
    ),
    default=Path.cwd(),
    show_default=True,
    help="Workspace directory, will default to current working directory.",
)
@click.option(
    "--module-registry",
    type=click.Path(
        exists=True,
        file_okay=False,
        path_type=Path,
        dir_okay=True,
    ),
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
    module_registry,
    workspace_dir,
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
        # First resolve path to ensure its absolute
        module_registry_path = module_registry.absolute()
        registry = FileSystemModuleRegistry(registry_path=module_registry_path)
        valid_module_names = registry.module_names()
        storage = FileSystemExperimentStorage(workspace_dir)

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
                "[muted] Note: Skipping sealevel step because no sealevel modules were passed to `feb setup-experiment --sealevel-step`. [/muted]"
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

        testing_schemas = {}
        for m in skeleton.all_module_names:
            try:
                testing_schemas[m] = registry.get_schema(m)
            except ValidationError as e:
                raise ValueError(f"shcema validation failed for module: '{m}") from e
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

        try:
            validate_module_names(
                skeleton.all_module_names, valid_modules=valid_module_names
            )
        except ValueError as e:
            raise ValueError(
                f"{e}\nCheck for typos or run 'uv run list-modules' to see available modules."
            ) from e

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
            shared_input_data=shared_input_data,
            projection_scale=projection_scale,
            definition=registry,  # registry passed as protocol
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
