"""CLI command for initializing a FACTS workspace."""

import click
from pathlib import Path

from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.init_workspace import (
    init_workspace,
    InitStepResult,
    StepStatus,
    REGISTRY_URL,
)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--registry-url",
    default=REGISTRY_URL,
    show_default=True,
    help="Git URL of the facts-module-registry to clone.",
)
def init(registry_url: str) -> None:
    """Initialize a FACTS workspace in the current directory.

    Creates experiments/, clones the module registry, and writes a
    .facts-workspace marker file. Safe to re-run on an already-initialized
    workspace.
    """
    workspace_dir = Path.cwd()

    console.rule(
        characters="- - ",
        style="rule",
        title="Initializing FACTS workspace",
    )
    console.print(f"[muted]Workspace: {workspace_dir}[/muted]\n")

    try:
        result = init_workspace(workspace_dir=workspace_dir, registry_url=registry_url)
    except OSError as e:
        raise click.UsageError(str(e))

    _print_step_result(1, "experiments/ directory", result.experiments_dir)
    _print_step_result(2, "facts-module-registry (git clone)", result.registry)

    if result.registry.status == StepStatus.FAILED:
        raise click.UsageError(
            f"Registry clone failed: {result.registry.message}\n"
            "Check your network connection and try again.\n"
            "If git interrupted a previous clone, remove the partial directory with:\n"
            "  rm -rf facts-module-registry/\nthen re-run feb init."
        )

    _print_step_result(3, ".gitignore (facts-module-registry/ entry)", result.gitignore)
    _print_step_result(4, ".facts-workspace marker", result.marker_file)

    console.print("\n[primary]Step 5:[/primary] Input data")
    console.print(
        "[muted]  Note: Guidance for downloading module input data will be available "
        "in a future update.[/muted]"
    )

    console.rule(
        style="rule",
        title="[success]Workspace ready![/success]",
    )
    console.print("\n[primary]Next steps:[/primary]")
    console.print("  [muted]1.[/muted] Download module input data")
    console.print(
        "  [muted]2.[/muted] Run [accent]feb setup-experiment[/accent] to configure an experiment"
    )


def _print_step_result(step_num: int, label: str, result: InitStepResult) -> None:
    console.print(f"[primary]Step {step_num}:[/primary] {label}")
    if result.status == StepStatus.CREATED:
        path_str = f" [secondary]{result.path}[/secondary]" if result.path else ""
        console.print(f"[success]  ✓ Created{path_str}[/success]")
    elif result.status == StepStatus.ALREADY_EXISTS:
        path_str = f" [secondary]{result.path}[/secondary]" if result.path else ""
        console.print(f"[muted]  Already exists —{path_str}[/muted]")
    elif result.status == StepStatus.FAILED:
        console.print(f"[danger]  ✗ {result.message}[/danger]")
    console.print()
