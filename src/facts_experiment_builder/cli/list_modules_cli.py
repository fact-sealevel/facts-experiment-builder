import click
from facts_experiment_builder.core.registry import ModuleRegistry


@click.command()
def list_modules():
    """List all modules in the registry. These are all of the modules that can be included in experiments built with facts-experiment-builder."""
    module_registry = ModuleRegistry.default()
    registry_location_message = f"I found a module registry at {module_registry.registry_dir}. This is what I'm using to see available modules."
    click.echo(registry_location_message)
    modules = module_registry.list_modules()
    click.echo("---")
    click.echo(f"Modules: {modules}")


if __name__ == "__main__":
    list_modules()
