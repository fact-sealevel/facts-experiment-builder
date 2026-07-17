import click
from facts_experiment_builder.cli.theme import console

from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
    unparse_module_list,
    validate_module_names,
)


def _collect_workflows(
    complete_modules_list: list[str],
    total_all_modules: bool,
) -> dict[str, str]:
    """Collects workflows from the user until they are done."""
    workflow_dict = {}
    if total_all_modules:
        workflow_name, module_list_str = _create_all_modules_workflow(
            complete_modules_list=complete_modules_list,
        )
        workflow_dict[workflow_name] = module_list_str.strip()

        if not click.confirm(
            "Received 'total_all_modules = True'. Do you want to define additional workflows with different combinations of modules?"
        ):
            return workflow_dict
    while True:
        workflow_name, module_list_str = _collect_single_workflow(
            complete_modules_list=complete_modules_list
        )
        workflow_dict[workflow_name] = module_list_str.strip()
        console.print(f"  Workflows so far: [secondary]{workflow_dict}[/secondary]")
        if not click.confirm(
            "Would you like to enter another workflow?", default=False
        ):
            break
    return workflow_dict


def _collect_single_workflow(complete_modules_list: list[str]) -> tuple[str, str]:
    """
    Prompts user to enter a name for a workflow followed by the modules to include in the workflow.
    Once workflow is received from user, parses response and validates against list of modules included in experiment to ensure no invalid modules.
    Returns: tuple(workflow_name, str of modules in workflow separated by ',' )
    """
    workflow_name = click.prompt(
        "Enter a name for this workflow (e.g. wf1)",
        type=str,
    )
    module_list_str = click.prompt(
        "Enter the names of the modules to include in this workflow, separated by commas",
        type=str,
    )
    module_list = parse_module_list_str(module_list_str)
    _validate_modules_list_workflow(module_list, complete_modules_list)
    return (workflow_name, module_list_str)


def _create_all_modules_workflow(complete_modules_list: list[str]) -> tuple[str, str]:
    """Creates an entry in workflows dict for all sealevel modules included in the experiment.
    Similar to _collect_single_workflow but with a fixed workflow name. Used for default "--total-all-modules=True".
    Returns: ("all-modules": [modules]]).

    """
    workflow_name = "all-modules"
    module_list = complete_modules_list
    module_list_str = unparse_module_list(module_list)
    return (workflow_name, module_list_str)


def _validate_modules_list_workflow(
    workflow_modules: list[str],
    experiment_modules: list[str],
) -> None:
    """Validates the modules listed for a workflow against the modules listed for the experiment."""
    try:
        validate_module_names(workflow_modules, experiment_modules)
    except ValueError as e:
        raise click.UsageError(
            f"{e} \nIt looks like you tried to add a module to a workflow that isn't included in the experiment, please fix this and continue."
        )
