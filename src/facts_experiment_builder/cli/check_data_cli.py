"""CLI command for checking a FACTS data directory against the module registry."""

import click
from pathlib import Path

from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.check_data import check_module_data
from facts_experiment_builder.core.registry.module_registry import ModuleRegistry


def resolve_input_paths(
    data_dir: Path,
    module_specific_input_data: Path | None,
    shared_input_data: Path | None,
) -> tuple[Path, Path]:
    """Resolve and validate module-specific and shared input data paths.

    Valid combinations:
        - data_dir only: expects module_specific_input_data/ and shared_input_data/ subdirs
        - Either or both explicit paths: override the corresponding data_dir-derived subdir
        - Both explicit paths: data_dir is ignored for resolution

    Raises:
        ValueError: if a resolved path does not exist on disk
    """
    module_dir = module_specific_input_data or data_dir / "module_specific_input_data"
    shared_dir = shared_input_data or data_dir / "shared_input_data"

    if not module_dir.exists():
        if module_specific_input_data:
            raise ValueError(
                f"Module-specific input data directory not found: {module_dir}\n"
                "Create it and download module input data first. See the quickstart guide."
            )
        existing_subdirs = [p.name for p in data_dir.iterdir() if p.is_dir()]
        raise ValueError(
            f"Expected subdirectory not found: {data_dir}/module_specific_input_data\n"
            f"Existing subdirectories at {data_dir}: {existing_subdirs}. "
            "Names MUST match 'module_specific_input_data' and 'shared_input_data'\n"
            "Either create this subdirectory and add module data, or specify the correct "
            "path with --module-specific-input-data."
        )

    if not shared_dir.exists():
        if shared_input_data:
            raise ValueError(
                f"Shared input data directory not found: {shared_dir}\n"
                "Create it and add shared input data first. See the quickstart guide."
            )
        raise ValueError(
            f"Expected subdirectory not found: {data_dir}/shared_input_data\n"
            "Either create this subdirectory and add shared data, or specify the correct "
            "path with --shared-input-data."
        )

    return module_dir, shared_dir


def check_provided_paths(
    data_dir: Path,
    module_specific_input_data: Path | None,
    shared_input_data: Path | None,
) -> tuple[Path, Path]:
    try:
        return resolve_input_paths(data_dir, module_specific_input_data, shared_input_data)
    except ValueError as e:
        raise click.UsageError(str(e))

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
def check_data(
    data_dir: Path,
    module_specific_input_data: Path | None,
    shared_input_data: Path | None,
) -> None:
    """Check a FACTS data directory against expected module inputs.

    Scans module_specific_input_data/ for downloaded modules and verifies
    that all expected input files are present based on the module registry.
    Modules are detected automatically from subdirectory names — only modules
    you have downloaded data for will be checked.
    """

    module_dir, shared_dir = check_provided_paths(
        data_dir=data_dir,
        module_specific_input_data=module_specific_input_data,
        shared_input_data=shared_input_data,
    )

    console.rule(characters="- - ", style="rule", title="Checking FACTS data directory")
    console.print(f"[muted]Module-specific inputs: {module_dir}[/muted]")
    console.print(f"[muted]Shared inputs:           {shared_dir}[/muted]\n")

    registry = check_registry_accessible()

    result = check_module_data(
        module_specific_input_dir=module_dir,
        shared_input_dir=shared_dir,
        registry=registry,
    )

    if not result.module_results and not result.unrecognized_dirs:
        console.print("[muted]No module data directories found under:[/muted]")
        console.print(f"[muted]  {module_dir}[/muted]")
        return

    any_missing = False

    for module_result in result.module_results:
        if module_result.n_checkable == 0:
            console.print(
                f"[muted]{module_result.module_name}: no checkable inputs[/muted]"
            )
            continue

        n_present = module_result.n_present
        n_total = module_result.n_checkable

        if module_result.n_missing == 0:
            console.print(
                f"[success]✓ {module_result.module_name}[/success] "
                f"[muted]({n_present}/{n_total} files present)[/muted]"
            )
        else:
            any_missing = True
            console.print(
                f"[danger]✗ {module_result.module_name}[/danger] "
                f"[muted]({n_present}/{n_total} files present)[/muted]"
            )
            for check in module_result.checks:
                if not check.skipped and not check.exists:
                    console.print(
                        f"  [danger]missing:[/danger] [secondary]{check.expected_path}[/secondary]"
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
