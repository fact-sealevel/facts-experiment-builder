"""Tests for prepare_execution_plan()."""

from unittest.mock import MagicMock

import pytest

from facts_experiment_builder.application import prepare_plan
from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from tests.unit.helpers import make_config_raw

_DATA_PATHS = ExperimentDataPaths(
    shared_input_data="/in/shared",
    module_specific_input_base="/in/module",
    output_data_location="/apptainer/out",
    experiment_specific_input_data=None,
)


def _config(**overrides) -> LoadedExperimentConfig:
    # No modules listed, so no schemas are parsed; module_schemas only needs to be
    # non-empty.
    return LoadedExperimentConfig.from_dict(
        make_config_raw(module_schemas={"unused": {}}, **overrides)
    )


_WORKFLOWS = {"wf1": MagicMock(), "wf2": MagicMock()}


def _experiment() -> MagicMock:
    """A global-scale experiment with a climate module and no totaling or ESL step, so
    the workflow check passes with or without workflows."""
    experiment = MagicMock(projection_scale="global")
    experiment.climate_step.module_name = "fair"
    experiment.sealevel_step.module_names = []
    experiment.totaling_step.is_present = False
    experiment.extreme_sealevel_step.is_present = False
    return experiment


def _stub_planning(monkeypatch, standard_specs, workflows=_WORKFLOWS, seen=None):
    """Replace planning steps with stubs; record the data_paths each one is given."""
    seen = {} if seen is None else seen

    def record(name, result):
        def fake(*args, **kwargs):
            seen[name] = kwargs.get("data_paths", args[-1] if args else None)
            return result

        return fake

    # Stub the experiment and workflows so these tests exercise only how
    # prepare_execution_plan() combines the spec builders' results.
    monkeypatch.setattr(
        prepare_plan,
        "FactsExperiment",
        MagicMock(from_loaded_config=lambda *a, **k: _experiment()),
    )
    monkeypatch.setattr(prepare_plan, "workflows_from_mapping", lambda m: workflows)
    monkeypatch.setattr(
        prepare_plan, "_build_standard_specs", record("standard", standard_specs)
    )
    monkeypatch.setattr(
        prepare_plan,
        "_build_facts_total_specs_for_workflows",
        record("facts_total", {"ft": MagicMock()}),
    )
    monkeypatch.setattr(
        prepare_plan,
        "_build_esl_specs_for_workflows",
        record("esl", {"esl": MagicMock()}),
    )
    return seen


def test_data_paths_are_passed_through_unchanged(monkeypatch):
    """The caller's data_paths reach every spec builder, so a relocated output root
    (Apptainer) is not replaced by one resolved from metadata."""
    seen = _stub_planning(monkeypatch, {"fair": MagicMock()})

    prepare_plan.prepare_execution_plan(_config(), _DATA_PATHS)

    assert seen == {
        "standard": _DATA_PATHS,
        "facts_total": _DATA_PATHS,
        "esl": _DATA_PATHS,
    }


def test_plan_carries_specs_climate_name_and_workflow_names(monkeypatch):
    fair = MagicMock()
    _stub_planning(monkeypatch, {"fair": fair})

    exec_plan = prepare_plan.prepare_execution_plan(_config(), _DATA_PATHS)

    assert exec_plan.standard_specs == {"fair": fair}
    assert list(exec_plan.facts_total_specs) == ["ft"]
    assert list(exec_plan.esl_specs) == ["esl"]
    assert exec_plan.climate_service_name == "fair"
    assert exec_plan.workflow_names == ["wf1", "wf2"]
    assert exec_plan.suppress_output_types == {"local"}


def test_without_workflows_no_facts_total_or_esl_specs_are_built(monkeypatch):
    seen = _stub_planning(monkeypatch, {"fair": MagicMock()}, workflows={})

    exec_plan = prepare_plan.prepare_execution_plan(_config(), _DATA_PATHS)

    assert set(seen) == {"standard"}
    assert exec_plan.facts_total_specs == {}
    assert exec_plan.esl_specs == {}


def test_no_modules_with_supplied_step_data_returns_empty_plan(monkeypatch):
    seen = _stub_planning(monkeypatch, {})

    exec_plan = prepare_plan.prepare_execution_plan(
        _config(**{"experiment-specific-input-data": "/in/exp"}), _DATA_PATHS
    )

    assert set(seen) == {"standard"}
    assert exec_plan.standard_specs == {}
    assert exec_plan.facts_total_specs == {}
    assert exec_plan.esl_specs == {}
    assert exec_plan.climate_service_name is None
    assert exec_plan.suppress_output_types == {"local"}
    assert exec_plan.workflow_names == ["wf1", "wf2"]


def test_no_modules_and_no_step_data_raises(monkeypatch):
    _stub_planning(monkeypatch, {})

    with pytest.raises(ValueError, match="No modules could be created"):
        prepare_plan.prepare_execution_plan(_config(), _DATA_PATHS)
