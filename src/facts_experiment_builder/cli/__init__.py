from facts_experiment_builder.cli.setup_new_experiment_cli import main as setup_new_experiment_group
from facts_experiment_builder.cli.generate_compose_cli import main as generate_compose_group
import click

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass

main.add_command(setup_new_experiment_group, name='setup-new-experiment')
main.add_command(generate_compose_group, name='generate-compose')