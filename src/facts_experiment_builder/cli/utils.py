"""Shared CLI utilities."""

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
