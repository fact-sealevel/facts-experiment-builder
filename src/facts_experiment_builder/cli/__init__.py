import click

from facts_experiment_builder.cli.init_cli import init
from facts_experiment_builder.cli.setup_experiment_cli import (
    main as setup_new_experiment_group,
)
from facts_experiment_builder.cli.generate_compose_cli import (
    main as generate_compose_group,
)
from facts_experiment_builder.cli.list_modules_cli import main as list_modules
from facts_experiment_builder.cli.check_data_cli import (
    main as check_data_main,
)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass


main.add_command(init, name="init")
main.add_command(setup_new_experiment_group, name="setup-experiment")
main.add_command(generate_compose_group, name="generate-compose")
main.add_command(list_modules, name="list-modules")
main.add_command(check_data_main, name="check-data")
