import click
from pathlib import Path
import yaml
from typing import Optional
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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--experiment-name",
    type=str,
    required=True,
    help="Name of the experiment (will look in experiments/ directory)"
)
@click.option(
    "--custom-output-path",
    type=click.Path(),
    default=None,
    help="Output path for compose file. If not provided, will use ../experiment_dir/experiment-compose.yaml. If provided, must include full path to file and use filename 'experiment-compose.yaml'"
)
def main(
    experiment_name, 
    custom_output_path: Optional[str] = None,
    ) -> None:
    """Generate Docker Compose file from experiment metadata."""

    metadata_path = find_experiment_metadata_file(experiment_name)
    
    message1 = f"Generating Docker Compose from: {metadata_path}"
    message2 = "=" * 70
    click.echo(message1)
    click.echo(message2)
    
    try:
        # Generate compose file as dict
        compose_dict = generate_compose_from_metadata(metadata_path)
    except Exception as e:
        logger.error(f"✗ Error generating compose content: {e}")
        raise click.ClickException(str(e))
    
    # Determine output path
    #if custom_output_path:
    #    output_path = Path(output).resolve()
    #else:
    #    output_path = experiment_dir / "experiment-compose.yaml"
    output_path = resolve_experiment_compose_path(metadata_path, custom_output_path)

 
    yaml_content = make_compose_yaml(content_dict=compose_dict)
    write_compose_yaml(
        compose_content=yaml_content,
        output_path=output_path,
    )

  
    message3 = "=" * 70
    click.echo(message3)
    message4 = f"✓ Generated Docker Compose file: {output_path}"
    click.echo(message4)

    #Print instructions for how to run experiment
    message5 = "\nTo run the experiment:"
    click.echo(message5)
    message6 = f"  docker compose -f {output_path.relative_to(Path.cwd())} up"
    click.echo(message6)
        
if __name__ == "__main__":
    main()