import logging
from pathlib import Path

import click

# ---------------------- Application imports ----------------------------
from facts_experiment_builder.application.generate_run_file import (
    generate_run_file,
)

# ---------------------- CLI imports ----------------------------
from facts_experiment_builder.cli.log_handler import configure_feb_logging
from facts_experiment_builder.cli.theme import console

# ---------------------- IO imports ----------------------------
from facts_experiment_builder.io.compose_backend import ComposeBackend
from facts_experiment_builder.io.experiment_repository import (
    StorageExperimentRepository,
)

logger = logging.getLogger(__name__)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment, including parent directory, if applicable.",
)
@click.option(
    "--custom-compose-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for compose file. If not provided, will use ../experiment_dir/experiment-compose.yaml. If provided, must include full path to file and use filename 'experiment-compose.yaml'",
)
@click.option(
    "--workspace-dir",
    type=click.Path(path_type=Path, exists=True, dir_okay=True, resolve_path=True),
    default=Path.cwd(),
    show_default=True,
    required=True,
    help="Workspace directory, will default to current working directory.",
)
@click.option(
    "--debug",
    default=False,
    is_flag=True,
    help="Enable debug mode",
)
def main(
    experiment_name: str,
    custom_compose_path: Path,
    workspace_dir: Path,
    debug,
) -> None:
    """Generate Docker Compose file from experiment metadata."""
    configure_feb_logging()

    experiment_repo = StorageExperimentRepository()
    if debug:
        logger.setLevel(logging.INFO)

    console.rule(style="rule")
    console.rule(
        style="rule", title="Generating Docker Compose file for specified experiment"
    )

    # Step 1: Find experiment metadata file

    console.print("[primary]Step 1:[/primary] Finding experiment metadata file...")

    # console.print(
    #    f"[success]✓ Found experiment metadata file:[/success] [secondary]{experiment_metadata_path}[/secondary]"
    # )
    # TODO in future, check it conforms to schema?

    try:
        output = generate_run_file(
            experiment_name=experiment_name,
            workspace_dir=workspace_dir,
            experiment_repo=experiment_repo,
            backend=ComposeBackend(),
            custom_output_path=custom_compose_path,
        )
        compose_path = output.path
    except (FileNotFoundError, ValueError) as e:  # need to incldue more errors ehre?
        console.print(f"[red]✗ Failed to generate compose file:[/red] {e}")
        raise SystemExit(1)

    console.print(
        f"[success]✓ Generated Docker Compose file:[/success] [secondary]{compose_path}[/secondary]"
    )
    console.print("\n[primary]Next steps:[/primary]")
    console.print(
        f"  [muted]1.[/muted] Run the experiment: [accent]docker compose -f {compose_path} up[/accent]"
    )
    console.rule(
        style="rule",
        title="[success]Docker Compose file generated successfully![/success]",
    )


if __name__ == "__main__":
    main()
