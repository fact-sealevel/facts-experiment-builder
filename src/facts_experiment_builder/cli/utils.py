"""Shared CLI utilities."""

from pathlib import Path
import logging
import click
from facts_experiment_builder.io.module_registry import (
    ModuleRegistryNotFound,
    FileSystemModuleRegistry,
)


def make_registry(registry_path: Path) -> FileSystemModuleRegistry:
    try:
        return FileSystemModuleRegistry(registry_path=registry_path.absolute())
    except ModuleRegistryNotFound as e:
        raise click.UsageError(
            f"Module registry not found at '{registry_path}"
            "Check where you are running this command from "
            " Also check that you have run `feb init`"
            f"Error: {e}"
        )

def configure_logging(debug_target):
    if not debug_target:
        return
    name = None if debug_target == "all" else debug_target
    logging.getLogger(name).setLevel(logging.INFO)
