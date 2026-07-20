import click
from facts_experiment_builder.cli.theme import console

# from facts_experiment_builder.cli.utils import check_registry_accessible
from pathlib import Path

from facts_experiment_builder.application.list_modules import (
    list_modules,
)


@click.command()
@click.option(
    "--module-registry",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    show_default=True,
    envvar="FEB_MODULE_REGISTRY_DIR",
    default=Path("./facts-module-registry"),
    help="Path to the facts-module-registry directory that is used in list-modules command.",
)
def main(module_registry):
    """List all modules in the registry.

    These are all of the modules that can be included in experiments built with facts-
    experiment-builder.
    """
    modules_names, registry_path = list_modules(registry_path=module_registry)

    console.rule(characters="- - ", style="rule", title="list-modules")
    console.print(
        f"You ran [bold]list-modules[/bold]. \n"
        f"Using the module registry at the following location: \n[secondary]{registry_path}[/secondary]."
    )

    console.print()
    console.print("The modules found in this registry are:")
    console.print()

    for module in modules_names:
        console.print(f"  [accent]→ {module}[/accent]")

    console.print()
    console.print(
        "🚨 [bold]Important[/bold] 🚨  \n"
        "This list is the modules that are in the local module registry, "
        "[italic]not[/italic] the modules for which input data has been downloaded. "
        "To see that, run [accent]feb check-data[/accent]."
    )


if __name__ == "__main__":
    main()
