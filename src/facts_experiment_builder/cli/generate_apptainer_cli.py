import logging
from pathlib import Path

import click

from facts_experiment_builder.application.generate_run_file import generate_run_file
from facts_experiment_builder.cli.log_handler import configure_feb_logging
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.io.apptainer_backend import ApptainerBackend
from facts_experiment_builder.io.experiment_repository import (
    StorageExperimentRepository,
)

logger = logging.getLogger(__name__)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment, including parent directory if applicable.",
)
@click.option(
    "--workspace-dir",
    type=click.Path(
        path_type=Path,
        exists=True,
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
    ),
    default=Path.cwd(),
    show_default=True,
    help="Workspace directory; defaults to current working directory.",
)
@click.option(
    "--custom-script-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path override for the generated script.",
)
@click.option(
    "--debug",
    default=False,
    is_flag=True,
    help="Enable debug mode.",
)
def main(
    experiment_name: str,
    workspace_dir: Path,
    custom_script_path: Path | None,
    debug: bool,
) -> None:
    """Generate Apptainer bash script from experiment metadata."""
    configure_feb_logging()

    experiment_repo = StorageExperimentRepository()
    if debug:
        logger.setLevel(logging.INFO)

    console.rule(style="rule")
    console.rule(
        style="rule", title="Generating Apptainer script for specified experiment"
    )
    console.print("[primary]Step 1:[/primary] Finding experiment metadata file...")

    try:
        output = generate_run_file(
            experiment_name=experiment_name,
            workspace_dir=workspace_dir,
            experiment_repo=experiment_repo,
            backend=ApptainerBackend(),
            custom_output_path=custom_script_path,
        )
        script_path = output.path
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗ Failed to generate Apptainer script:[/red] {e}")
        raise SystemExit(1)

    console.print(
        f"[success]✓ Generated Apptainer script:[/success] [secondary]{script_path}[/secondary]"
    )
    console.print("\n[primary]Next steps:[/primary]")
    console.print(
        f"  [muted]1.[/muted] Run the experiment: [accent]bash {script_path}[/accent]"
    )
    console.rule(
        style="rule",
        title="[success]Apptainer script generated successfully![/success]",
    )


if __name__ == "__main__":
    main()
