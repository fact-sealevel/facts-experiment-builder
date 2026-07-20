"""CLI command for checking a FACTS data directory against the module registry."""

import click
from pathlib import Path

from facts_experiment_builder.cli.theme import console

from facts_experiment_builder.application.check_data import (
    check_data,
    resolve_input_paths,
)

from facts_experiment_builder.infra.module_registry import FileSystemModuleRegistry


def check_provided_paths(
    data_dir: Path,
    module_specific_input_data: Path | None,
    shared_input_data: Path | None,
) -> tuple[Path, Path]:
    """Call resolve_input_paths on paths provided by user and raise click usage error if
    expected directories not found at provided paths."""
    try:
        return resolve_input_paths(
            data_dir, module_specific_input_data, shared_input_data
        )
    except ValueError as e:
        raise click.UsageError(str(e))


@click.command()
@click.option(
    "--data-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd() / "data",
    show_default=True,
    help="Base data directory. By default, expects module-specific and shared input data in "
    "module_specific_input_data/ and shared_input_data/ subdirectories. Can be overridden with "
    "--module-specific-input-data and --shared-input-data.",
)
@click.option(
    "--module-specific-input-data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Explicit path to module-specific input data directory. Overrides data_dir for this purpose.",
)
@click.option(
    "--shared-input-data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Explicit path to shared input data directory. Overrides data_dir for this purpose.",
)
@click.option(
    "--module-registry",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    show_default=True,
    envvar="FEB_MODULE_REGISTRY_DIR",
    default=Path("./facts-module-registry"),
    help="Path to the facts-module-registry directory to use in check-data. MUst be same as that used in setup-experiment. Default value points to the registry that is created if running from facts2-workspace after running `feb init`.",
)
def main(
    data_dir: Path,
    module_specific_input_data: Path | None,
    shared_input_data: Path | None,
    module_registry: Path,
) -> None:
    """Check a FACTS data directory against expected module inputs.

    Scans module_specific_input_data/ for downloaded modules and verifies that all
    expected input files are present based on the module registry. Modules are detected
    automatically from subdirectory names — only modules you have downloaded data for
    will be checked.
    """
    # Make registry
    registry_path = module_registry.absolute()
    registry = FileSystemModuleRegistry(registry_path=registry_path)
    # Check that provided paths are valid
    # Resolve paths checks if valid, check_provided_paths raises error if not
    module_dir, shared_dir = check_provided_paths(
        data_dir=data_dir,
        module_specific_input_data=module_specific_input_data,
        shared_input_data=shared_input_data,
    )

    # Print to user the paths that are checked
    console.rule(characters="- - ", style="rule", title="Checking FACTS data directory")
    console.print(f"[muted]Module-specific inputs: {module_dir}[/muted]")
    console.print(f"[muted]Shared inputs:           {shared_dir}[/muted]\n")

    # Call application layer function
    result = check_data(
        module_specific_input_dir=module_dir,
        shared_input_dir=shared_dir,
        definitions=registry,
    )

    # If there are no module results in the results object, print msg to user + return
    if not result.module_results and not result.unrecognized_dirs:
        console.print("[muted]No module data directories found under:[/muted]")
        console.print(f"[muted]  {module_dir}[/muted]")
        return

    any_missing = False

    for module_result in result.module_results:
        if module_result.n_checkable == 0:
            console.print(
                f"[success]☐ {module_result.module_name} [/success]:"
                " [muted] ~No checkable inputs~[/muted]"
            )
            continue

        n_present = module_result.n_present
        n_total = module_result.n_checkable

        if module_result.n_missing == 0:
            console.print(
                f"[success]✔ {module_result.module_name}[/success]: "
                f"[muted]({n_present}/{n_total} expected entries present)[/muted]"
            )
        else:
            any_missing = True
            console.print(
                f"[danger]✗ {module_result.module_name}[/danger]: "
                f"[muted]({n_present}/{n_total} expected entries present)[/muted]"
            )
            for check in module_result.checks:
                if not check.skipped and not check.exists:
                    console.print(
                        f"  [danger] ❗ missing:[/danger] [secondary]{check.expected_path}[/secondary]"
                    )

    if result.shared_checks:
        console.print()
        console.print("[bold]Shared input data:[/bold]")
        n_shared_present = sum(1 for c in result.shared_checks if c.exists)
        n_shared_total = len(result.shared_checks)
        if all(c.exists for c in result.shared_checks):
            console.print(
                f"[success]✓ shared_input_data[/success] "
                f"[muted]({n_shared_present}/{n_shared_total} files present)[/muted]"
            )
        else:
            any_missing = True
            console.print(
                f"[danger]✗ shared_input_data[/danger] "
                f"[muted]({n_shared_present}/{n_shared_total} files present)[/muted]"
            )
            for check in result.shared_checks:
                if not check.exists:
                    console.print(
                        f"  [danger]missing:[/danger] [secondary]{check.expected_path}[/secondary]"
                    )

    if any_missing:
        console.print()
        console.print(
            "[muted]To download missing files, see docs/module_input_data_downloads.md "
            "in the facts-experiment-builder repo. To see exactly which filenames a module "
            "expects, check the module's YAML in facts-module-registry.[/muted]"
        )

    if result.unrecognized_dirs:
        console.print()
        console.print(
            "[warning]Unrecognized directories (not in module registry):[/warning]"
        )
        for d in result.unrecognized_dirs:
            console.print(f"  [muted]{d}[/muted]")

    n_modules = len(result.module_results)
    n_issues = sum(1 for r in result.module_results if r.n_missing > 0)
    n_ok = n_modules - n_issues

    console.print()
    if n_issues == 0:
        console.rule(
            style="rule", title="[success]All checked modules look good![/success]"
        )
    else:
        console.rule(
            style="rule",
            title=f"[warning]{n_issues} module(s) have missing files[/warning]",
        )
    console.print(
        f"\n[muted]{n_modules} module(s) checked — "
        f"{n_ok} complete, {n_issues} with missing files[/muted]"
    )
