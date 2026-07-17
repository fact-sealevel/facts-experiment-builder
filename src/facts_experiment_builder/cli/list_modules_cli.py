import click
from facts_experiment_builder.cli.theme import console

# from facts_experiment_builder.cli.utils import check_registry_accessible
from pathlib import Path
from facts_experiment_builder.infra.module_registry import FileSystemModuleRegistry


@click.command()
@click.option(
    "--module-registry",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    show_default=True,
    envvar="FEB_MODULE_REGISTRY_DIR",
    default=Path("./facts-module-registry"),
    help="Path to the facts-module-registry directory that is used in list-modules command.",
)
def list_modules(module_registry):
    """List all modules in the registry. These are all of the modules that can be included in experiments built with facts-experiment-builder."""
    # First, ensure path is absoltue
    registry_path = module_registry.absolute()
    module_registry = FileSystemModuleRegistry(registry_path=registry_path)
    # module_registry = check_registry_accessible()

    console.rule(characters="- - ", style="rule", title="list-modules")
    console.print(
        f"You ran [bold]list-modules[/bold]. "
        f"I found a module registry at [secondary]{module_registry._registry_path}[/secondary]."
    )

    console.print()
    console.print("The modules found in this registry are:")
    console.print()
    module_names = module_registry.module_names()
    for module in sorted(module_names):
        console.print(f"  [accent]→ {module}[/accent]")

    console.print()
    console.print(
        "🚨 [bold]Important[/bold] 🚨  "
        "This list is the modules that are in the local module registry, "
        "[italic]not[/italic] the modules for which input data has been downloaded. "
        "To see that, run [accent]check-data[/accent]."
    )


if __name__ == "__main__":
    list_modules()
