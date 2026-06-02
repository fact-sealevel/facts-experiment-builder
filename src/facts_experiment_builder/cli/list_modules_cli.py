import click
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.cli.utils import check_registry_accessible

@click.command()
def list_modules():
    """List all modules in the registry. These are all of the modules that can be included in experiments built with facts-experiment-builder."""
    
    module_registry = check_registry_accessible()

    console.rule(characters="- - ", style="rule", title="list-modules")
    console.print(
        f"You ran [bold]list-modules[/bold]. "
        f"I found a module registry at [secondary]{module_registry.registry_dir}[/secondary]."
    )

    console.print()
    console.print("The modules found in this registry are:")
    console.print()
    for module in sorted(module_registry.list_modules()):
        console.print(f"  [accent]{module}[/accent]")

    console.print()
    console.print(
        "🚨 [bold]Important[/bold] 🚨  "
        "This list is the modules that are in the local module registry, "
        "[italic]not[/italic] the modules for which input data has been downloaded. "
        "To see that, run [accent]check-data[/accent]."
    )


if __name__ == "__main__":
    list_modules()
