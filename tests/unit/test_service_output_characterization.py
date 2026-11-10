"""Characterization tests for per-service and whole-file Compose / Apptainer output.

These pin the output of both generators so the re_org refactor (moving backend-specific
code out of core/, see plans/re_org_backend_neutral_service.md) can be checked for
behavior changes. Every assertion compares a whole value against a snapshot under
tests/unit/snapshots/, generated from the code before the refactor.

Only `_compose()` and `_apptainer()` should need to change across the refactor; a change
to a snapshot means the output changed.

To regenerate the snapshots (only when an output change is intended):
    FEB_UPDATE_SNAPSHOTS=1 uv run pytest tests/unit/test_service_output_characterization.py
"""

import dataclasses
import json
import os
from pathlib import Path
from typing import Any

import pytest

from facts_experiment_builder.application.generate_run_file import generate_run_file
from facts_experiment_builder.application.setup_experiment import (
    finalize_experiment_setup,
    prepare_experiment_setup,
)
from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleContainerImage,
    ModuleSchema,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
)
from facts_experiment_builder.io.apptainer_backend import ApptainerBackend
from facts_experiment_builder.io.apptainer_service import to_apptainer_service
from facts_experiment_builder.io.compose_backend import ComposeBackend
from facts_experiment_builder.io.compose_service import to_compose_service
from facts_experiment_builder.io.experiment_repository import (
    StorageExperimentRepository,
)
from facts_experiment_builder.io.module_registry import FileSystemModuleRegistry
from tests.unit.helpers import InMemoryModuleDefinitions

_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
_REGISTRY_DIR = Path(__file__).parent / "fixtures" / "module_registry"
_UPDATE = os.environ.get("FEB_UPDATE_SNAPSHOTS") == "1"


def _check_snapshot(name: str, actual: str) -> None:
    path = _SNAPSHOT_DIR / name
    if _UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual)
    assert path.exists(), f"Missing snapshot {path}; run with FEB_UPDATE_SNAPSHOTS=1"
    assert actual == path.read_text()


# ---------------------------------------------------------------------------
# The two calls that change across the refactor
# ---------------------------------------------------------------------------


def _compose(spec: ModuleServiceSpec, **kwargs: Any) -> dict[str, Any]:
    climate_service_name = kwargs.pop("climate_service_name", None)
    run = spec.to_service_run(**kwargs)
    return to_compose_service(
        run, depends_on=spec.dependencies(climate_service_name=climate_service_name)
    )


def _apptainer(spec: ModuleServiceSpec, **kwargs: Any) -> dict[str, Any]:
    suppress = kwargs.pop("suppress_output_types", None)
    run = spec.to_service_run(suppress_output_types=suppress)
    return dataclasses.asdict(to_apptainer_service(run, **kwargs))


# ---------------------------------------------------------------------------
# Per-service output
# ---------------------------------------------------------------------------

_OUTPUT_MOUNT = {
    "volume": "output",
    "container_path": "/mnt/out",
    "transform": "filename",
}
_MODULE_IN_MOUNT = {
    "volume": "module_specific_input",
    "container_path": "/mnt/module_specific_in",
}
_VOLUMES = {
    "output": {
        "host_path": "module_inputs.output_paths.output_dir",
        "container_path": "/mnt/out",
    },
    "module_specific_input": {
        "host_path": "module_inputs.input_paths.module_specific_input_dir",
        "container_path": "/mnt/module_specific_in",
    },
}


def _output_file(name: str, filename: str, output_type: str) -> dict[str, Any]:
    return {
        "name": name,
        "type": "file",
        "source": f"module_inputs.outputs.{name.replace('-', '_')}",
        "filename": filename,
        "output_type": output_type,
        "mount": _OUTPUT_MOUNT,
    }


def _spec(
    module_name: str = "my-module",
    *,
    image_url: str = "ghcr.io/fact-sealevel/my-module",
    image_tag: str = "0.1.0",
    inputs: list[dict[str, Any]] | None = None,
    input_values: dict[str, Any] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    output_values: dict[str, Any] | None = None,
    uses_climate_file: bool = False,
    depends_on: list[Any] | None = None,
    output_container_base: str | None = None,
) -> ModuleServiceSpec:
    schema_dict: dict[str, Any] = {
        "module_name": module_name,
        "container_image": f"{image_url}:{image_tag}",
        "arguments": {
            "inputs": inputs or [],
            "outputs": {"files": outputs or []},
        },
        "volumes": _VOLUMES,
        "uses_climate_file": uses_climate_file,
    }
    if depends_on is not None:
        schema_dict["depends_on"] = depends_on
    components = ModuleServiceSpecComponents(
        module_name=module_name,
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/in",
            module_specific_input_dir=f"/in/module/{module_name}",
            shared_input_dir="/in/shared",
        ),
        output_paths=ModuleOutputPaths(
            output_dir=f"/out/{module_name}", output_type="global"
        ),
        fingerprint_params={},
        inputs=input_values or {},
        outputs=output_values or {},
        image=ModuleContainerImage(image_url=image_url, image_tag=image_tag),
        top_level_params=TopLevelParams(),
        output_container_base=output_container_base,
    )
    return ModuleServiceSpec(
        components=components, module_definition=ModuleSchema.from_dict(schema_dict)
    )


def _with_outputs(**kwargs: Any) -> ModuleServiceSpec:
    return _spec(
        outputs=[
            _output_file("output-gslr-file", "gslr.nc", "global"),
            _output_file("output-lslr-file", "lslr.nc", "local"),
        ],
        output_values={
            "output_gslr_file": "/out/my-module/gslr.nc",
            "output_lslr_file": "/out/my-module/lslr.nc",
        },
        **kwargs,
    )


def _with_envvar() -> ModuleServiceSpec:
    return _spec(
        inputs=[
            {
                "name": "forcing-head-path",
                "type": "str",
                "source": "module_inputs.inputs.forcing_head_path",
                "envvar": "EMULANDICE_FORCING_HEAD_PATH",
                "mount": _MODULE_IN_MOUNT,
            }
        ],
        input_values={"forcing_head_path": "forcing"},
    )


def _climate_dependent(**kwargs: Any) -> ModuleServiceSpec:
    return _spec(
        inputs=[
            {
                "name": "climate-data-file",
                "type": "str",
                "source": "module_inputs.inputs.climate_data_file",
                "climate_step_output": "output-climate-file",
                "external_volume": True,
                "mount": _OUTPUT_MOUNT,
            }
        ],
        input_values={"climate_data_file": "/out/fair-temperature/climate.nc"},
        uses_climate_file=True,
        **kwargs,
    )


# name -> (spec factory, compose kwargs, apptainer kwargs)
_CASES: dict[str, tuple[Any, dict[str, Any], dict[str, Any]]] = {
    "plain": (lambda: _spec(), {}, {}),
    "outputs": (_with_outputs, {}, {}),
    "outputs-suppress-local": (
        _with_outputs,
        {"suppress_output_types": {"local"}},
        {"suppress_output_types": {"local"}},
    ),
    "envvar": (_with_envvar, {}, {}),
    "climate-dependent-with-climate-service": (
        _climate_dependent,
        {"climate_service_name": "fair-temperature"},
        {"wait_for_files": ["/out/fair-temperature/climate.nc"]},
    ),
    "climate-dependent-no-climate-service": (_climate_dependent, {}, {}),
    "schema-depends-on": (
        lambda: _climate_dependent(
            depends_on=[
                "fair",
                "other-plain",
                {"service": "other-with-condition", "condition": "service_started"},
                {"service": "other-no-condition"},
                {"service": "fair", "condition": "service_healthy"},
            ]
        ),
        {"climate_service_name": "fair-temperature"},
        {},
    ),
    "facts-total-style": (
        lambda: _spec(
            "facts-total-wf1-global",
            outputs=[_output_file("output-path", "wf1_global_total.nc", "global")],
            output_values={"output_path": "/out/facts-total/wf1_global_total.nc"},
            output_container_base="/mnt/total_out/facts-total",
        ),
        {},
        {"run_in_background": True, "pid_var": "PID_FACTS_TOTAL_WF1_GLOBAL"},
    ),
    "image-no-registry": (lambda: _spec(image_url="img"), {}, {}),
    "image-trailing-slash": (
        lambda: _spec(image_url="ghcr.io/fact-sealevel/img/"),
        {},
        {},
    ),
}


def test_per_service_output_matches_snapshot():
    actual = {
        name: {
            "compose": _compose(factory(), **compose_kwargs),
            "apptainer": _apptainer(factory(), **apptainer_kwargs),
        }
        for name, (factory, compose_kwargs, apptainer_kwargs) in _CASES.items()
    }
    _check_snapshot(
        "service_output.json", json.dumps(actual, indent=2, sort_keys=False) + "\n"
    )


# ---------------------------------------------------------------------------
# Whole generated files
# ---------------------------------------------------------------------------

_EXPERIMENT_NAME = "experiments/snapshot"


def _setup_experiment(workspace_dir: Path, projection_scale: str) -> None:
    registry = FileSystemModuleRegistry(_REGISTRY_DIR.resolve())
    definitions = InMemoryModuleDefinitions(
        {name: registry.get_schema(name) for name in registry.module_names()}
    )
    prepared = prepare_experiment_setup(
        experiment_name=_EXPERIMENT_NAME,
        module_regions=None,
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step="ssp-landwaterstorage,tlm-sterodynamics,emulandice-ais",
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step="extremesealevel-pointsoverthreshold",
        workspace_dir=workspace_dir,
    )
    finalize_experiment_setup(
        experiment_name=_EXPERIMENT_NAME,
        experiment_paths=prepared.experiment_paths,
        experiment_skeleton=prepared.experiment_skeleton,
        workflows_dict={
            "wf1": "ssp-landwaterstorage",
            "wf2": "tlm-sterodynamics,emulandice-ais",
        },
        pipeline_id="abc123",
        scenario="ssp585",
        baseyear=2005,
        pyear_start=2020,
        pyear_end=2150,
        pyear_step=10,
        nsamps=50,
        location_file="location.lst",
        module_specific_input_data=str(workspace_dir / "data" / "module"),
        shared_input_data=str(workspace_dir / "data" / "shared"),
        projection_scale=projection_scale,
        module_registry=definitions,
        experiment_repo=StorageExperimentRepository(),
    )


def _normalize(text: str, tmp_path: Path) -> str:
    # tmp_path may appear resolved (/private/var/...) or not (/var/...) on macOS.
    for prefix in sorted(
        {str(tmp_path.resolve()), str(tmp_path)}, key=len, reverse=True
    ):
        text = text.replace(prefix, "<TMP>")
    return text


@pytest.mark.parametrize("projection_scale", ["local", "global"])
def test_generated_files_match_snapshot(tmp_path, projection_scale):
    workspace_dir = tmp_path / "workspace"
    (workspace_dir / "experiments").mkdir(parents=True)
    _setup_experiment(workspace_dir, projection_scale)
    repo = StorageExperimentRepository()

    compose = generate_run_file(
        experiment_name=_EXPERIMENT_NAME,
        workspace_dir=workspace_dir,
        experiment_repo=repo,
        backend=ComposeBackend(),
    )
    apptainer = generate_run_file(
        experiment_name=_EXPERIMENT_NAME,
        workspace_dir=workspace_dir,
        experiment_repo=repo,
        backend=ApptainerBackend(),
    )

    _check_snapshot(
        f"experiment-compose.{projection_scale}.yaml",
        _normalize(compose.path.read_text(), tmp_path),
    )
    _check_snapshot(
        f"experiment-apptainer.{projection_scale}.sh",
        _normalize(apptainer.path.read_text(), tmp_path),
    )
