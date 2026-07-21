import click
from pathlib import Path
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.generate_compose import (
    generate_compose,
)
from facts_experiment_builder.cli.utils import (
    determine_root,
)

from facts_experiment_builder.infra.experiment_storage import (
    FileSystemExperimentStorage,
)
from facts_experiment_builder.infra.experiment_loader import load_experiment_metadata
from facts_experiment_builder.infra.module_registry import FileSystemModuleRegistry
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.infra.write_compose import (
    make_compose_yaml,
    write_compose_yaml,
)
import logging

logger = logging.getLogger(__name__)


_SUCCESS = 25  # must match application layer value
logging.addLevelName(_SUCCESS, "SUCCESS")


class _ClickEchoHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if record.levelno >= logging.WARNING:
            console.print(f"⚠ [danger]Warning: [/danger]{msg}")
        elif record.levelno == _SUCCESS:
            console.print(f"✓ [success]{msg}[/success]")
        else:  # INFO
            console.print(f"ℹ [accent]{msg}[/accent]")


def _configure_feb_logging() -> None:
    """Wire the ClickEchoHandler onto the facts_experiment_builder namespace logger.

    Called at CLI invocation time (not import time) so that tests importing from sibling
    modules don't accidentally install the handler and break caplog capture.
    """
    feb_logger = logging.getLogger("facts_experiment_builder")
    if not any(isinstance(h, _ClickEchoHandler) for h in feb_logger.handlers):
        feb_logger.addHandler(_ClickEchoHandler())
    feb_logger.setLevel(logging.INFO)
    feb_logger.propagate = False


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment, including parent directory, if applicable.",
)
@click.option(
    "--custom-output-path",
    type=click.Path(),
    default=None,
    help="Output path for compose file. If not provided, will use ../experiment_dir/experiment-compose.yaml. If provided, must include full path to file and use filename 'experiment-compose.yaml'",
)
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    default=None,
    show_default=True,
    help="Project root directory, will default to current working directory.",
)
@click.option(
    "--debug",
    default=False,
    is_flag=True,
    help="Enable debug mode",
)
@click.option(
    "--module-registry",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    show_default=True,
    envvar="FEB_MODULE_REGISTRY_DIR",
    default=Path("./facts-module-registry"),
    help="Path to the facts-module-registry directory to use in generate-compose. MUst be same as that used in setup-experiment. Default value points to the registry that is created if running from facts2-workspace after running `feb init`.",
)
def main(
    experiment_name,
    custom_output_path,
    root,
    module_registry,
    debug,
) -> None:
    """Generate Docker Compose file from experiment metadata."""
    _configure_feb_logging()
    module_registry_path = module_registry.absolute()
    registry = FileSystemModuleRegistry(registry_path=module_registry_path)

    if debug:
        logger.setLevel(logging.INFO)

    console.rule(style="rule")
    console.rule(
        style="rule", title="Generating Docker Compose file for specified experiment"
    )

    # Step 1: Find experiment metadata file
    console.print("[primary]Step 1:[/primary] Finding experiment metadata file...")

    exp = ExperimentName.parse(experiment_name)
    storage = FileSystemExperimentStorage(determine_root(root))

    experiment_path = storage.experiment_dir(exp)
    output_path = (
        custom_output_path.resolve()
        if custom_output_path is not None
        else storage.compose_path(exp)
    )

    assert experiment_path.is_dir(), f"Expected '{experiment_path}' to be a directory."
    # experiment_directory_exists(experiment_directory=experiment_path)
    # then, get path to config file
    experiment_metadata_path = storage.config_path(exp=exp)
    # experiment_metadata_path = make_experiment_metadata_path_from_experiment_dir(
    #    experiment_path=experiment_path
    # )
    # Ensure the file exists
    assert experiment_metadata_path.exists(), (
        f"Expected '{experiment_metadata_path}' exists."
    )
    # experiment_metadata_file_exists(experiment_metadata_path)

    console.print(
        f"[success]✓ Found experiment metadata file:[/success] [secondary]{experiment_metadata_path}[/secondary]"
    )
    # TODO in future, check it conforms to schema?

    # # Step 2: Build compose dictionary from metadata
    console.print(
        "[primary]Step 2:[/primary] Building compose dictionary from metadata..."
    )
    # check that file exists at metadata path
    if not experiment_metadata_path.exists():
        raise FileNotFoundError(
            f"When trying to read experiment-metadata file to generate corresponding "
            f"compose file, metadata file not found: {experiment_metadata_path}"
        )
    # Load experiment metadata file in as dict
    metadata_dict = load_experiment_metadata(experiment_metadata_path)

    try:
        compose_dict = generate_compose(
            metadata=metadata_dict,
            experiment_dir=experiment_metadata_path.parent,
            definition=registry,
        )
    except (FileNotFoundError, ValueError) as e:  # need to incldue more errors ehre?
        console.print(f"[red]✗ Failed to generate compose file:[/red] {e}")
        raise SystemExit(1)

    # Step 3: Resolve output path for compose file
    console.print(
        "[primary]Step 3:[/primary] Resolving output path for compose file..."
    )
    # Check if received custom output path to use
    # if custom_output_path is not None:
    #     # add fn here
    #     output_path = resolve_custom_experiment_compose_path(custom_output_path)
    # else:
    #     output_path = resolve_default_experiment_compose_path(
    #         experiment_path=experiment_path
    #     )

    # # Step 4: Make compose YAML content from dict
    console.print("[primary]Step 4:[/primary] Making compose YAML content from dict...")
    yaml_content = make_compose_yaml(content_dict=compose_dict)

    # # Step 5: Write compose YAML content to file
    console.print("[primary]Step 5:[/primary] Writing compose YAML content to file...")
    write_compose_yaml(
        compose_content=yaml_content,
        output_path=output_path,
    )
    console.print(
        f"[success]✓ Generated Docker Compose file:[/success] [secondary]{output_path}[/secondary]"
    )
    console.print("\n[primary]Next steps:[/primary]")
    console.print(
        f"  [muted]1.[/muted] Run the experiment: [accent]docker compose -f {output_path.relative_to(Path.cwd())} up[/accent]"
    )
    console.rule(
        style="rule",
        title="[success]Docker Compose file generated successfully![/success]",
    )


if __name__ == "__main__":
    main()
