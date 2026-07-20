"""Shared CLI utilities."""

from pathlib import Path
import logging
import click
from facts_experiment_builder.infra.module_registry import (
    ModuleRegistryNotFound,
    FileSystemModuleRegistry,
)


def make_registry(registry_path: Path) -> FileSystemModuleRegistry:
    try:
        return FileSystemModuleRegistry(registry_path=registry_path.absolute())
    except ModuleRegistryNotFound:
        raise click.UsageError(
            f"Module registry not found at '{registry_path}"
            "Check where you are running this command from "
            " Also check that you have run `feb init`"
        )


def determine_root(cli_root: Path | None) -> Path:
    """For determining the project root directory that will be used for setting up and
    organizing experiment direcotries and files.

    If user provides a root path in `setup-experiment`, this will be prioritized.
    Otherwise takes cwd. Always returns a resolved absolute path.
    """
    if cli_root:
        return cli_root.resolve(strict=True)
    return Path.cwd().resolve(strict=True)


def configure_logging(debug_target):
    if not debug_target:
        return
    name = None if debug_target == "all" else debug_target
    logging.getLogger(name).setLevel(logging.INFO)
