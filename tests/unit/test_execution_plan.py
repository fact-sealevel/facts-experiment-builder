"""Tests for the execution_plan module."""

from facts_experiment_builder.application import execution_plan as execution_plan_module
from facts_experiment_builder.application.execution_plan import (
    _collect_workflow_output_paths_by_type,
)
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.workflow import Workflow


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

    def fake_build(metadata, module_name, known_module_names, module_definition):
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
    )

    assert (
        captured["inputs"]["gesla-dir"] == "/data/module_specific_input_data/gesla_data"
    )
    assert "total-localsl-file" in captured["inputs"]
