"""Tests for the generate_compose module."""

import pytest
from facts_experiment_builder.application import generate_compose
from facts_experiment_builder.core.experiment.experiment_plan import (
    check_metadata_has_required_fields,
)
from facts_experiment_builder.application.generate_compose import (
    _validate_climate_file_inputs,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema


def _make_climate_schema(input_name: str) -> ModuleSchema:
    source_key = input_name.replace("-", "_")
    return ModuleSchema(
        module_name="test-module",
        container_image="img:tag",
        uses_climate_file=True,
        arguments={
            "inputs": [
                {
                    "name": input_name,
                    "type": "str",
                    "source": f"module_inputs.inputs.{source_key}",
                    "mount": {"volume": "output", "container_path": "/mnt/out"},
                }
            ]
        },
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
    )


def test_validate_climate_file_inputs_passes_with_standard_key():
    """Validation succeeds when the module's climate input key is provided in metadata."""
    schema = _make_climate_schema("climate-data-file")
    metadata = {
        "test-module": {"inputs": {"climate_data_file": "fair-temperature/climate.nc"}}
    }
    _validate_climate_file_inputs(metadata, ["test-module"], {"test-module": schema})


def test_validate_climate_file_inputs_passes_with_nonstandard_key():
    """Validation succeeds when the module uses a non-standard climate input name."""
    schema = _make_climate_schema("input-data-file")
    metadata = {
        "test-module": {"inputs": {"input_data_file": "fair-temperature/climate.nc"}}
    }
    _validate_climate_file_inputs(metadata, ["test-module"], {"test-module": schema})


def test_validate_climate_file_inputs_raises_when_nonstandard_key_missing():
    """Validation raises when a module with a non-standard climate input name has no value."""
    schema = _make_climate_schema("input-data-file")
    metadata = {"test-module": {"inputs": {}}}
    with pytest.raises(ValueError, match="test-module"):
        _validate_climate_file_inputs(
            metadata, ["test-module"], {"test-module": schema}
        )


# ---------------------------------------------------------------------------
# projection_scale == "global" suppression
# ---------------------------------------------------------------------------


def _make_workflow_metadata(mod: str = "tlm-sterodynamics") -> dict:
    """Minimal metadata dict for _collect_workflow_output_paths_by_type tests."""
    return {
        mod: {
            "outputs": {
                "output-gslr-file": {
                    "value": f"{mod}/gslr.nc",
                    "output_type": "global",
                },
                "output-lslr-file": {"value": f"{mod}/lslr.nc", "output_type": "local"},
            }
        }
    }


def _make_module_schema(mod: str, file_outputs: list) -> ModuleSchema:
    return ModuleSchema(
        module_name=mod,
        container_image="img:tag",
        arguments={"outputs": {"files": file_outputs}},
        volumes={},
    )


def test_collect_workflow_output_paths_global_only():
    """Only global outputs are collected when output_type='global'."""
    from facts_experiment_builder.core.workflow import Workflow

    wf = Workflow(name="wf1", module_names=["tlm-sterodynamics"])
    metadata = _make_workflow_metadata()
    paths = generate_compose._collect_workflow_output_paths_by_type(
        metadata, wf, "global", {}
    )
    assert len(paths) == 1
    assert "gslr.nc" in paths[0]


def test_collect_workflow_output_paths_local_only():
    """Only local outputs are collected when output_type='local'."""
    from facts_experiment_builder.core.workflow import Workflow

    wf = Workflow(name="wf1", module_names=["tlm-sterodynamics"])
    metadata = _make_workflow_metadata()
    paths = generate_compose._collect_workflow_output_paths_by_type(
        metadata, wf, "local", {}
    )
    assert len(paths) == 1
    assert "lslr.nc" in paths[0]


def test_collect_workflow_output_paths_excludes_pass_to_total_false():
    """Outputs with pass_to_total=False in the schema are excluded."""
    from facts_experiment_builder.core.workflow import Workflow

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
                "source": "s",
                "output_type": "global",
                "pass_to_total": True,
            },
            {
                "name": "output-gslr-wais-file",
                "type": "file",
                "source": "s",
                "output_type": "global",
                "pass_to_total": False,
            },
        ],
    )
    paths = generate_compose._collect_workflow_output_paths_by_type(
        metadata, wf, "global", {mod: schema}
    )
    assert len(paths) == 1
    assert "gslr.nc" in paths[0]
    assert "wais" not in paths[0]


def test_collect_workflow_output_paths_no_schema_includes_all():
    """When a module has no entry in schemas, all its outputs pass through."""
    from facts_experiment_builder.core.workflow import Workflow

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
    paths = generate_compose._collect_workflow_output_paths_by_type(
        metadata, wf, "global", {}
    )
    assert len(paths) == 2


def test_check_metadata_has_required_fields():
    required_fields = {
        "experiment-name": "my-test-exp",
        "pipeline-id": "abc123",
        "nsamps": 100,
    }
    metadata_complete = {
        "experiment-name": "my-test-exp",
        "pipeline-id": "abc123",
        "nsamps": 100,
        "scenario": "ssp585",
    }
    metadata_incomplete = {
        "pipeline-id": "abc123",
        "nsamps": 100,
        "experiment-name": None,
    }
    check_metadata_has_required_fields(metadata_complete, required_fields)

    with pytest.raises(ValueError, match="experiment-name"):
        check_metadata_has_required_fields(
            metadata_incomplete, required_fields=["experiment-name"]
        )


def test_extract_all_module_names_returns_all_modules():
    metadata = {
        "climate_module": "fair-temperature",
        "sealevel_modules": ["bamber19-icesheets", "tlm-sterodynamics"],
        "framework_modules": ["facts-total"],
        "esl_modules": ["extremesealevel-pointsoverthreshold"],
    }
    result = generate_compose._extract_all_module_names_from_manifest(metadata)
    assert result == [
        "fair-temperature",
        "bamber19-icesheets",
        "tlm-sterodynamics",
        "facts-total",
        "extremesealevel-pointsoverthreshold",
    ]


def test_extract_all_module_names_excludes_none_temperature():
    metadata = {
        "temperature_module": "NONE",
        "sealevel_modules": ["tlm-sterodynamics"],
        "framework_modules": [],
        "esl_modules": [],
    }
    result = generate_compose._extract_all_module_names_from_manifest(metadata)
    assert result == ["tlm-sterodynamics"]


def test_extract_all_module_names_excludes_lowercase_none_temperature():
    metadata = {"temperature_module": "none", "sealevel_modules": ["tlm-sterodynamics"]}
    result = generate_compose._extract_all_module_names_from_manifest(metadata)
    assert result == ["tlm-sterodynamics"]


def test_extract_all_module_names_empty_metadata():
    result = generate_compose._extract_all_module_names_from_manifest({})
    assert result == []
