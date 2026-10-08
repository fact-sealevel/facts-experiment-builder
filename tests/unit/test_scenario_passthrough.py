"""The experiment's scenario is passed unchanged to every module.

ssp-landwaterstorage used to map the scenario name (e.g. ssp585 -> ssp5) via a
`scenario_name_ssp_landwaterstorage` transform and a scenario_name_mapping file in its
registry entry. That special case is removed: every module, including
ssp-landwaterstorage, receives the scenario exactly as set at setup. The
ssp-landwaterstorage schema below still declares the old transform and mapping, as the
registry YAML does, to show they no longer change the value.
"""

from pathlib import Path

import pytest
import yaml

from facts_experiment_builder.application.generate_compose import generate_compose
from facts_experiment_builder.application.setup_experiment import (
    finalize_experiment_setup,
    prepare_experiment_setup,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.io.experiment_repository import (
    StorageExperimentRepository,
)
from tests.unit.helpers import InMemoryModuleDefinitions, make_schema

_EXPERIMENT_NAME = "experiments/scenario_test"

_SCENARIO_ARG = {
    "name": "scenario",
    "type": "str",
    "source": "metadata.scenario",
    "optional": True,
}


def _schema_with_scenario_arg(name: str, **scenario_arg_extra) -> ModuleSchema:
    return make_schema(
        name,
        arguments={"top_level": [{**_SCENARIO_ARG, **scenario_arg_extra}]},
    )


def _ssp_landwaterstorage_schema() -> ModuleSchema:
    """As in the registry: scenario arg with the old transform, plus a mapping file."""
    schema = _schema_with_scenario_arg(
        "ssp-landwaterstorage", transform="scenario_name_ssp_landwaterstorage"
    )
    schema.extra["scenario_name_mapping"] = {
        "ssp585": "ssp5",
        "ssp245": "ssp2",
        "ssp126": "ssp1",
    }
    return schema


def _registry() -> InMemoryModuleDefinitions:
    return InMemoryModuleDefinitions(
        {
            "fair-temperature": _schema_with_scenario_arg("fair-temperature"),
            "ssp-landwaterstorage": _ssp_landwaterstorage_schema(),
            "tlm-sterodynamics": _schema_with_scenario_arg("tlm-sterodynamics"),
            # arguments={}: make_schema's default empty lists are written to
            # experiment-config.yaml as blank values, which don't reload (see notes).
            "facts-total": make_schema("facts-total", arguments={}),
        }
    )


def _setup_experiment(workspace_dir: Path, scenario: str) -> Path:
    prepared = prepare_experiment_setup(
        experiment_name=_EXPERIMENT_NAME,
        module_regions=None,
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step="ssp-landwaterstorage,tlm-sterodynamics",
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step=None,
        workspace_dir=workspace_dir,
    )
    return finalize_experiment_setup(
        experiment_name=_EXPERIMENT_NAME,
        experiment_paths=prepared.experiment_paths,
        experiment_skeleton=prepared.experiment_skeleton,
        workflows_dict={},
        pipeline_id="abc123",
        scenario=scenario,
        baseyear=2005,
        pyear_start=2020,
        pyear_end=2150,
        pyear_step=10,
        nsamps=50,
        location_file="location.lst",
        module_specific_input_data="path/to/data",
        shared_input_data="path/to/shared/data",
        projection_scale="local",
        module_registry=_registry(),
        experiment_repo=StorageExperimentRepository(),
    )


@pytest.fixture
def workspace(tmp_path) -> Path:
    workspace_dir = tmp_path / "workspace"
    (workspace_dir / "experiments").mkdir(parents=True)
    return workspace_dir


# Common names that the old ssp-landwaterstorage mapping changed, plus one it didn't.
_SCENARIOS = ["ssp585", "ssp245", "ssp126", "my-custom-scenario"]


@pytest.mark.parametrize("scenario", _SCENARIOS)
def test_setup_records_scenario_unchanged(workspace, scenario):
    config_path = _setup_experiment(workspace, scenario)
    config = yaml.safe_load(config_path.read_text())
    assert config["scenario"] == scenario


@pytest.mark.parametrize("scenario", _SCENARIOS)
def test_every_module_receives_scenario_unchanged(workspace, scenario):
    _setup_experiment(workspace, scenario)
    output = generate_compose(
        experiment_name=_EXPERIMENT_NAME,
        workspace_dir=workspace,
        experiment_repo=StorageExperimentRepository(),
    )
    services = output.compose_dict["services"]

    scenario_args = {
        name: [arg for arg in svc["command"] if arg.startswith("--scenario=")]
        for name, svc in services.items()
    }
    # Every module that declares a scenario arg gets exactly one, with the
    # experiment's scenario as-is.
    for name in ("fair-temperature", "ssp-landwaterstorage", "tlm-sterodynamics"):
        assert scenario_args[name] == [f"--scenario={scenario}"], name
