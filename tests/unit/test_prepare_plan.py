"""Tests for prepare_execution_plan()."""

from unittest.mock import MagicMock

from facts_experiment_builder.application import prepare_plan
from facts_experiment_builder.application.execution_plan import _ModuleSpecs
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)

_DATA_PATHS = ExperimentDataPaths(
    shared_input_data="/in/shared",
    module_specific_input_base="/in/module",
    output_data_location="/apptainer/out",
    experiment_specific_input_data=None,
)

# No modules listed, so no schemas are parsed; module_schemas only needs to be non-empty.
_METADATA = {"module_schemas": {"unused": {}}}


def _specs(**kwargs) -> _ModuleSpecs:
    fields = dict(
        climate_module=None, sealevel_modules={}, framework_modules={}, esl_modules={}
    )
    fields.update(kwargs)
    return _ModuleSpecs(**fields)


def test_data_paths_are_passed_through_unchanged(monkeypatch):
    """The caller's data_paths reach spec building and the execution plan, so a
    relocated output root (Apptainer) is not replaced by one resolved from metadata."""
    seen = {}
    plan = MagicMock()
    exec_plan = MagicMock()

    def fake_build_module_specs(**kwargs):
        seen["specs"] = kwargs["data_paths"]
        return _specs(sealevel_modules={"m": MagicMock()})

    def fake_build_execution_plan(**kwargs):
        seen["exec"] = kwargs["data_paths"]
        return exec_plan

    monkeypatch.setattr(prepare_plan, "_make_experiment_plan", lambda m, s: plan)
    monkeypatch.setattr(prepare_plan, "_build_module_specs", fake_build_module_specs)
    monkeypatch.setattr(
        prepare_plan, "build_experiment_execution_plan", fake_build_execution_plan
    )

    result = prepare_plan.prepare_execution_plan(_METADATA, _DATA_PATHS)

    assert result == (plan, exec_plan)
    assert seen == {"specs": _DATA_PATHS, "exec": _DATA_PATHS}


def test_no_module_specs_returns_empty_execution_plan(monkeypatch):
    plan = MagicMock(suppress_output_types={"local"})

    def fail(**kwargs):
        raise AssertionError("execution plan should not be built without specs")

    monkeypatch.setattr(prepare_plan, "_make_experiment_plan", lambda m, s: plan)
    monkeypatch.setattr(prepare_plan, "_build_module_specs", lambda **kw: _specs())
    monkeypatch.setattr(prepare_plan, "build_experiment_execution_plan", fail)

    _plan, exec_plan = prepare_plan.prepare_execution_plan(_METADATA, _DATA_PATHS)

    assert exec_plan.standard_specs == {}
    assert exec_plan.facts_total_specs == {}
    assert exec_plan.esl_specs == {}
    assert exec_plan.climate_service_name is None
    assert exec_plan.suppress_output_types == {"local"}
