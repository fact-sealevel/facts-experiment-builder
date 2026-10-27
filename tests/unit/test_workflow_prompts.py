import click
import pytest

from facts_experiment_builder.cli import workflow_prompts
from facts_experiment_builder.cli.workflow_prompts import (
    _collect_workflows,
    _create_all_modules_workflow,
    _resolve_workflows,
    _validate_modules_list_workflow,
)
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
)
from facts_experiment_builder.core.experiment.skeleton import ExperimentSkeleton


def _skeleton(sealevel_step: str | None, supplied: str | None = None):
    return ExperimentSkeleton.from_inputs(
        climate_step="fair-temperature" if not supplied else None,
        supplied_climate_step_data=None,
        sealevel_step=sealevel_step,
        supplied_totaled_sealevel_step_data=supplied,
        extremesealevel_step=None,
    )


def _fail_if_prompted(*args, **kwargs):
    raise AssertionError("user was prompted for workflows")


# --- _resolve_workflows ---


@pytest.mark.parametrize("supplied", [None, "data.nc"])
def test_resolve_workflows_empty_without_totaling(monkeypatch, supplied):
    monkeypatch.setattr(workflow_prompts, "_collect_workflows", _fail_if_prompted)
    skeleton = _skeleton(None, supplied)
    assert _resolve_workflows(skeleton, total_all_modules=False) == {}


@pytest.mark.parametrize("total_all_modules", [True, False])
def test_resolve_workflows_single_module_creates_all_modules_without_prompt(
    monkeypatch, total_all_modules
):
    monkeypatch.setattr(workflow_prompts, "_collect_workflows", _fail_if_prompted)
    skeleton = _skeleton("tlm-sterodynamics")
    assert _resolve_workflows(skeleton, total_all_modules=total_all_modules) == {
        "all-modules": "tlm-sterodynamics"
    }


def test_resolve_workflows_multiple_modules_collects_from_user(monkeypatch):
    captured = {}

    def fake_collect(complete_modules_list, total_all_modules):
        captured["args"] = (complete_modules_list, total_all_modules)
        return {"wf1": "a"}

    monkeypatch.setattr(workflow_prompts, "_collect_workflows", fake_collect)
    skeleton = _skeleton("a,b")
    assert _resolve_workflows(skeleton, total_all_modules=True) == {"wf1": "a"}
    assert captured["args"] == (["a", "b"], True)


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


# --- _validate_modules_list_workflow ---


def test_validate_modules_list_workflow_raises_for_invalid_module():
    """A module not present in the experiment's module list raises click.UsageError."""
    with pytest.raises(click.UsageError, match="invalid-module"):
        _validate_modules_list_workflow(
            workflow_modules=["ipccar5-icesheets", "invalid-module"],
            experiment_modules=["ipccar5-icesheets", "ipccar5-glaciers"],
        )


def test_validate_modules_list_workflow_passes_for_valid_modules():
    """No error is raised when all workflow modules are in the experiment."""
    _validate_modules_list_workflow(
        workflow_modules=["ipccar5-icesheets"],
        experiment_modules=["ipccar5-icesheets", "ipccar5-glaciers"],
    )


# --- _collect_workflows wiring: invalid module entered at the prompt ---


def test_usage_error_propagates_when_module_not_in_experiment_added_in_workflow(
    monkeypatch,
):
    """An invalid module entered at the prompt surfaces as click.UsageError through
    the full _collect_workflows loop (wiring check; validation rules themselves are
    covered by the _validate_modules_list_workflow tests above)."""
    modules = ["ipccar5-icesheets", "ipccar5-glaciers"]

    prompts = iter(["wf1", "ipccar5-icesheets,invalid-module"])
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: next(prompts))

    with pytest.raises(click.UsageError):
        _collect_workflows(complete_modules_list=modules, total_all_modules=False)
