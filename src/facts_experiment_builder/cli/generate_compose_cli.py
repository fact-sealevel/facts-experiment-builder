import click
from pathlib import Path
from typing import Optional
from facts_experiment_builder.cli.theme import console
from facts_experiment_builder.application.generate_compose import (
    generate_compose_from_metadata,
)
from facts_experiment_builder.infra.path_manager import (
    find_experiment_metadata_file,
    resolve_experiment_compose_path,
)
from facts_experiment_builder.infra.write_compose import (
    make_compose_yaml,
    write_compose_yaml,
)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment (will look in experiments/ directory)",
)
@click.option(
    "--custom-output-path",
    type=click.Path(),
    default=None,
    help="Output path for compose file. If not provided, will use ../experiment_dir/experiment-compose.yaml. If provided, must include full path to file and use filename 'experiment-compose.yaml'",
)
def main(
    experiment_name,
    custom_output_path: Optional[str] = None,
) -> None:
    """Generate Docker Compose file from experiment metadata."""
    console.rule(style="rule")
    console.rule(
        style="rule", title="Generating Docker Compose file for specified experiment"
    )

    # Step 1: Find experiment metadata file
    console.print("[primary]Step 1:[/primary] Finding experiment metadata file...")
    metadata_path = find_experiment_metadata_file(experiment_name)
    console.print(
        f"[success]✓ Found experiment metadata file:[/success] [secondary]{metadata_path}[/secondary]"
    )

    # Step 2: Build compose dictionary from metadata
    console.print(
        "[primary]Step 2:[/primary] Building compose dictionary from metadata..."
    )
    try:
        compose_dict = generate_compose_from_metadata(metadata_path)
    except Exception as e:
        console.print(f"[danger]✗ Error generating compose content: {e}[/danger]")
        raise click.ClickException(str(e))

    # Step 3: Resolve output path for compose file
    console.print(
        "[primary]Step 3:[/primary] Resolving output path for compose file..."
    )
    output_path = resolve_experiment_compose_path(metadata_path, custom_output_path)

    # Step 4: Make compose YAML content from dict
    console.print("[primary]Step 4:[/primary] Making compose YAML content from dict...")
    yaml_content = make_compose_yaml(content_dict=compose_dict)

    # Step 5: Write compose YAML content to file
    console.print("[primary]Step 5:[/primary] Writing compose YAML content to file...")
    write_compose_yaml(
        compose_content=yaml_content,
        output_path=output_path,
    )
    console.print("[primary]Step 6:[/primary] Print success message...")
    console.print(
        f"[success]✓ Generated Docker Compose file:[/success] [secondary]{output_path}[/secondary]"
    )
    console.print("\n[primary]Next steps:[/primary]")
    console.print(
        f"  [muted]1.[/muted] Run the experiment: [accent]docker compose -f {output_path.relative_to(Path.cwd())} up[/accent]"
    )
    console.rule(
        style="rule",
        title="[success]Docker Compose file generated successfully![/success]",
    )


if __name__ == "__main__":
    main()
