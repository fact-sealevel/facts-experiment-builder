"""Shared CLI utilities."""

from pathlib import Path
import logging
import click
from facts_experiment_builder.core.registry import ModuleRegistry


def check_registry_accessible():
    try:
        registry = ModuleRegistry.default()
        return registry
    except FileNotFoundError as e:
        raise click.UsageError(
            f"{e}\n"
            "Are you running this from your FACTS workspace root? "
            "If not, cd there and re-run. If you haven't set up a workspace yet, "
            "run `feb init` first."
        )


def determine_root(cli_root: Path | None) -> Path:
    """
    For determining the project root directory that will be used for setting up and organizing experiment direcotries and files.
    If user provides a root path in `setup-experiment`, this will be prioritized. Otherwise takes cwd.
    Always returns a resolved absolute path.
    """
    if cli_root:
        return cli_root.resolve(strict=True)
    return Path.cwd().resolve(strict=True)


def configure_logging(debug_target):
    if not debug_target:
        return
    name = None if debug_target == "all" else debug_target
    logging.getLogger(name).setLevel(logging.INFO)
