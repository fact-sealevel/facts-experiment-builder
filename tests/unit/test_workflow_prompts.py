import click
from facts_experiment_builder.cli.workflow_prompts import (
    _collect_workflows,
    _create_all_modules_workflow,
)
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
)
# def test_validate_modules_list_workflow_passes_for_valid():
#     experiment_modules_list = [
#         "ipccar5-icesheets",
#         "ipccar5-glaciers",
#         "ssp-landwaterstorage",
#     ]
#     workflow_modules_list = [
#         "ipccar5-icesheets",
#         "ipccar5-glaciers",
#     ]
#     _validate_modules_list_workflow(workflow_modules_list, experiment_modules_list)


# def test_validate_modules_list_workflow_fails_for_invalid():
#     experiment_modules_list = [
#         "ipccar5-icesheets",
#         "ipccar5-glaciers",
#         "ssp-landwaterstorage",
#     ]
#     workflow_modules_list = [
#         "ipccar5-icesheets",
#         "ipccar5-glaciers",
#         "tlm-sterodynamics",
#     ]
#     with pytest.raises(click.UsageError):
#         _validate_modules_list_workflow(workflow_modules_list, experiment_modules_list)


# @pytest.mark.parametrize(
#     "step_module, step_data, expectation",
#     [
#         ("a-module", None, nullcontext()),
#         (None, "/path/to/data", nullcontext()),
#         ("a-module", "/path/to/data", pytest.raises(click.UsageError)),
#         (None, None, pytest.raises(click.UsageError)),
#     ],
# )
# def test_check_experiment_step(step_module, step_data, expectation):
#     with expectation:
#         _check_required_experiment_step(
#             step_module, step_data, "--step-module", "--step-data"
#         )


# --- _create_all_modules_workflow ---


def test_create_all_modules_workflow_key_is_all_modules():
    modules = ["ipccar5-icesheets", "ipccar5-glaciers", "tlm-sterodynamics"]
    name, values = _create_all_modules_workflow(modules)
    # turn values from str to list
    values_list = parse_module_list_str(values)
    assert name == "all-modules"
    assert values_list == modules, f"Expected: {modules}, received: {values}"


def test_create_all_modules_workflow_value_contains_all_sealevel_modules():
    modules = ["ipccar5-icesheets", "ipccar5-glaciers", "tlm-sterodynamics"]
    _, modules_str = _create_all_modules_workflow(modules)
    for module in modules:
        assert module in modules_str


# --- _collect_workflows with total_all_modules=True ---


def test_collect_workflows_total_all_modules_true_adds_all_modules_entry(monkeypatch):
    """When total_all_modules=True, workflow_dict must contain 'all-modules' key
    mapping to all sealevel modules passed as complete_modules_list."""
    modules = ["ipccar5-icesheets", "ipccar5-glaciers"]

    # Provide one additional workflow via prompts, then decline to add more
    prompts = iter(["wf1", "ipccar5-icesheets"])
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: next(prompts))
    monkeypatch.setattr(click, "confirm", lambda *args, **kwargs: False)

    workflow_dict = _collect_workflows(
        complete_modules_list=modules, total_all_modules=True
    )

    assert "all-modules" in workflow_dict
    for module in modules:
        assert module in workflow_dict["all-modules"]


def test_collect_workflows_total_all_modules_false_no_all_modules_entry(monkeypatch):
    """When total_all_modules=False, no 'all-modules' key is added automatically."""
    modules = ["ipccar5-icesheets", "ipccar5-glaciers"]

    prompts = iter(["wf1", "ipccar5-icesheets"])
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: next(prompts))
    monkeypatch.setattr(click, "confirm", lambda *args, **kwargs: False)

    workflow_dict = _collect_workflows(
        complete_modules_list=modules, total_all_modules=False
    )

    assert "all-modules" not in workflow_dict
