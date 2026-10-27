"""Tests for the execution_plan module."""

from unittest.mock import MagicMock

import pytest

from facts_experiment_builder.application import execution_plan as execution_plan_module
from facts_experiment_builder.cli import workflow_prompts
from facts_experiment_builder.cli.workflow_prompts import _resolve_workflows
from facts_experiment_builder.application.execution_plan import (
    _collect_workflow_output_paths_by_type,
    _ModuleSpecs,
    build_experiment_execution_plan,
)
from facts_experiment_builder.core.experiment.experiment_plan import _ExperimentPlan
from facts_experiment_builder.core.experiment.skeleton import ExperimentSkeleton
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.core.workflow import Workflow, workflows_from_metadata

_DATA_PATHS = ExperimentDataPaths(
    shared_input_data="/in/shared",
    module_specific_input_base="/in/module",
    output_data_location="/out",
    experiment_specific_input_data=None,
)


def _make_workflow_metadata(mod: str = "tlm-sterodynamics") -> dict:
    """Minimal metadata dict for _collect_workflow_output_paths_by_type tests."""
    return {
        mod: {
            "outputs": {
                "output-gslr-file": {
                    "value": f"{mod}/gslr.nc",
                    "output_type": "global",
                },
                "output-lslr-file": {
                    "value": f"{mod}/lslr.nc",
                    "output_type": "local",
                },
            }
        }
    }


def _make_module_schema(mod: str, file_outputs: list) -> ModuleSchema:
    return ModuleSchema(
        module_name=mod,
        container_image="img:tag",
        arguments=ArgumentsSpec.model_validate({"outputs": {"files": file_outputs}}),
        volumes={},
    )


def _make_esl_schema(module_name: str) -> ModuleSchema:
    return ModuleSchema(
        module_name=module_name,
        container_image="img:tag",
        arguments=ArgumentsSpec.model_validate(
            {
                "inputs": [
                    {
                        "name": "total-localsl-file",
                        "type": "file",
                        "source": "module_inputs.inputs.total_localsl_file",
                        "mount": {"volume": "output", "container_path": "/mnt/out"},
                    },
                    {
                        "name": "gesla-dir",
                        "type": "dir",
                        "source": "module_inputs.inputs.gesla_dir",
                        "mount": {
                            "volume": "module_specific_in",
                            "container_path": "/mnt/module_specific_in",
                        },
                    },
                ]
            }
        ),
        volumes={
            "output": {"host_path": "module_inputs.output_paths.output_dir"},
        },
    )


def _patch_build_module_service_spec(monkeypatch, captured):
    """Stub out build_module_service_spec so these tests exercise only
    _build_esl_specs_for_workflows' own input-building logic, not the full
    (filesystem-touching) service-spec build pipeline."""

    def fake_build(
        metadata, module_name, known_module_names, module_definition, data_paths
    ):
        captured["inputs"] = dict(metadata[module_name]["inputs"])

        class _Stub:
            pass

        return _Stub()

    monkeypatch.setattr(execution_plan_module, "build_module_service_spec", fake_build)


def test_collect_workflow_output_paths_global_only():
    """Only global outputs are collected when output_type='global'."""
    wf = Workflow(name="wf1", module_names=["tlm-sterodynamics"])
    metadata = _make_workflow_metadata()
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "global", {})
    assert len(paths) == 1
    assert "gslr.nc" in paths[0]


def test_collect_workflow_output_paths_local_only():
    """Only local outputs are collected when output_type='local'."""
    wf = Workflow(name="wf1", module_names=["tlm-sterodynamics"])
    metadata = _make_workflow_metadata()
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "local", {})
    assert len(paths) == 1
    assert "lslr.nc" in paths[0]


def test_collect_workflow_output_paths_excludes_pass_to_total_false():
    """Outputs with pass_to_total=False in the schema are excluded."""
    mod = "emulandice-ais"
    wf = Workflow(name="wf1", module_names=[mod])
    metadata = {
        mod: {
            "outputs": {
                "output-gslr-file": {
                    "value": f"{mod}/gslr.nc",
                    "output_type": "global",
                },
                "output-gslr-wais-file": {
                    "value": f"{mod}/gslr-wais.nc",
                    "output_type": "global",
                },
            }
        }
    }
    schema = _make_module_schema(
        mod,
        [
            {
                "name": "output-gslr-file",
                "type": "file",
                "source": "module_inputs.outputs.output_gslr_file",
                "output_type": "global",
                "pass_to_total": True,
            },
            {
                "name": "output-gslr-wais-file",
                "type": "file",
                "source": "module_inputs.outputs.output_gslr_wais_file",
                "output_type": "global",
                "pass_to_total": False,
            },
        ],
    )
    paths = _collect_workflow_output_paths_by_type(
        metadata, wf, "global", {mod: schema}
    )
    assert len(paths) == 1
    assert "gslr.nc" in paths[0]
    assert "wais" not in paths[0]


def test_collect_workflow_output_paths_no_schema_includes_all():
    """When a module has no entry in schemas, all its outputs pass through."""
    mod = "unknown-module"
    wf = Workflow(name="wf1", module_names=[mod])
    metadata = {
        mod: {
            "outputs": {
                "output-a": {"value": f"{mod}/a.nc", "output_type": "global"},
                "output-b": {"value": f"{mod}/b.nc", "output_type": "global"},
            }
        }
    }
    paths = _collect_workflow_output_paths_by_type(metadata, wf, "global", {})
    assert len(paths) == 2


# ---------------------------------------------------------------------------
# _build_esl_specs_for_workflows — inputs pass through unmodified, no synthesized
# defaults (any per-input default belongs in that input's own arg-spec
# `default_value`, resolved generically like any other input — not hardcoded here)
# ---------------------------------------------------------------------------


def test_build_esl_specs_does_not_synthesize_missing_inputs(monkeypatch):
    """A declared input with no value in metadata is left absent — no default is
    fabricated, regardless of the input's name."""
    captured = {}
    _patch_build_module_service_spec(monkeypatch, captured)

    module_name = "extremesealevel-pointsoverthreshold"
    schema = _make_esl_schema(module_name)
    wf = Workflow(name="wf1", module_names=[module_name])
    metadata = {module_name: {"inputs": {}, "outputs": {}}}

    execution_plan_module._build_esl_specs_for_workflows(
        esl_module_names=[module_name],
        workflows={"wf1": wf},
        metadata=metadata,
        projection_scale=None,
        schemas={module_name: schema},
        data_paths=_DATA_PATHS,
    )

    assert "gesla-dir" not in captured["inputs"]


def test_build_esl_specs_passes_through_provided_inputs(monkeypatch):
    """Inputs already present in metadata are carried through unmodified, alongside
    the injected total-localsl-file."""
    captured = {}
    _patch_build_module_service_spec(monkeypatch, captured)

    module_name = "extremesealevel-pointsoverthreshold"
    schema = _make_esl_schema(module_name)
    wf = Workflow(name="wf1", module_names=[module_name])
    metadata = {
        module_name: {
            "inputs": {"gesla-dir": "/data/module_specific_input_data/gesla_data"},
            "outputs": {},
        }
    }

    execution_plan_module._build_esl_specs_for_workflows(
        esl_module_names=[module_name],
        workflows={"wf1": wf},
        metadata=metadata,
        projection_scale=None,
        schemas={module_name: schema},
        data_paths=_DATA_PATHS,
    )

    assert (
        captured["inputs"]["gesla-dir"] == "/data/module_specific_input_data/gesla_data"
    )
    assert "total-localsl-file" in captured["inputs"]


# ---------------------------------------------------------------------------
# facts-total -> ESL wiring (#146): every ESL service depends on and reads from its
# workflow's facts-total-local service, including with a single sea-level module.
# ---------------------------------------------------------------------------

_ESL_MODULE = "extremesealevel-pointsoverthreshold"


def _sealevel_metadata(modules: list[str], n_local_outputs: int) -> dict:
    return {
        m: {
            "outputs": {
                "output-gslr-file": {"value": f"{m}/gslr.nc", "output_type": "global"},
                **{
                    f"output-lslr-{i}-file": {
                        "value": f"{m}/lslr-{i}.nc",
                        "output_type": "local",
                    }
                    for i in range(n_local_outputs)
                },
            }
        }
        for m in modules
    }


def _build_wired_plan(monkeypatch, sealevel_step, projection_scale, n_local_outputs=1):
    """Skeleton -> _resolve_workflows -> execution plan for an experiment with an ESL
    module. Returns (execution plan, its one workflow, {service: metadata section})."""
    built_sections: dict[str, dict] = {}

    def fake_build(metadata, module_name, **_kwargs):
        built_sections[module_name] = metadata[module_name]
        return MagicMock()

    monkeypatch.setattr(execution_plan_module, "build_module_service_spec", fake_build)
    # Stands in for the interactive prompts reached with multiple modules
    monkeypatch.setattr(
        workflow_prompts,
        "_collect_workflows",
        lambda complete_modules_list, total_all_modules: {
            "wf1": ",".join(complete_modules_list)
        },
    )

    skeleton = ExperimentSkeleton.from_inputs(
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step=sealevel_step,
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step=_ESL_MODULE,
    )
    workflows = workflows_from_metadata(
        {"workflows": _resolve_workflows(skeleton, total_all_modules=False)}
    )
    modules = skeleton.sealevel_modules
    schemas = {
        "facts-total": ModuleSchema(
            module_name="facts-total",
            container_image="img:tag",
            arguments=ArgumentsSpec(),
            volumes={},
            per_workflow=True,
        ),
        _ESL_MODULE: _make_esl_schema(_ESL_MODULE),
        **{m: _make_module_schema(m, []) for m in modules},
    }
    plan = _ExperimentPlan(
        experiment=MagicMock(projection_scale=projection_scale),
        climate_module_name="fair-temperature",
        sealevel_module_names=modules,
        framework_module_names=[skeleton.totaling_module],
        esl_module_names=[_ESL_MODULE],
        suppress_output_types={"local"} if projection_scale == "global" else set(),
        workflows=workflows,
    )
    specs = _ModuleSpecs(
        climate_module=None,
        sealevel_modules={m: MagicMock() for m in modules},
        framework_modules={},
        esl_modules={_ESL_MODULE: MagicMock()},
    )
    exec_plan = build_experiment_execution_plan(
        specs=specs,
        plan=plan,
        metadata=_sealevel_metadata(modules, n_local_outputs),
        schemas=schemas,
        data_paths=_DATA_PATHS,
    )
    (wf,) = workflows.values()
    return exec_plan, wf, built_sections


@pytest.mark.parametrize("sealevel_step", ["a", "a,b"])  # "a" is #146
def test_esl_depends_on_and_reads_facts_total_local(monkeypatch, sealevel_step):
    exec_plan, wf, built = _build_wired_plan(monkeypatch, sealevel_step, "local")
    local_total = wf.facts_total_service_name_for_type("local")
    global_total = wf.facts_total_service_name_for_type("global")
    esl_service = f"{_ESL_MODULE}-{wf.name}"

    assert set(exec_plan.facts_total_specs) == {local_total, global_total}
    assert set(exec_plan.esl_specs) == {esl_service}
    _, depends_on = exec_plan.esl_specs[esl_service]
    assert depends_on == local_total
    assert (
        built[esl_service]["inputs"]["total-localsl-file"]
        == wf.total_localsl_path_under_output
    )


@pytest.mark.parametrize("sealevel_step", ["a", "a,b"])
def test_global_scale_runs_only_global_total_and_no_esl(monkeypatch, sealevel_step):
    exec_plan, wf, _ = _build_wired_plan(monkeypatch, sealevel_step, "global")
    assert set(exec_plan.facts_total_specs) == {
        wf.facts_total_service_name_for_type("global")
    }
    assert exec_plan.esl_specs == {}


def test_single_module_sends_all_its_local_outputs_to_facts_total(monkeypatch):
    _, wf, built = _build_wired_plan(monkeypatch, "a", "local", n_local_outputs=2)
    local_total = wf.facts_total_service_name_for_type("local")
    assert sorted(built[local_total]["inputs"]["item"]) == [
        "/mnt/total_out/a/lslr-0.nc",
        "/mnt/total_out/a/lslr-1.nc",
    ]
