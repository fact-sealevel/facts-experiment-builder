"""Each run command writes to the output location in experiment-config.yaml for that
command, as written: compose-output-data-location for generate-compose and
apptainer-output-data-location for generate-apptainer. setup-experiment writes
defaults for both. generate-compose still reads the deprecated output-data-location."""

import logging
from pathlib import Path

import pytest
import yaml

from facts_experiment_builder.application.generate_apptainer import generate_apptainer
from facts_experiment_builder.application.generate_compose import generate_compose
from facts_experiment_builder.core.module.module_service_path_resolution import (
    APPTAINER_OUTPUT_KEY,
    COMPOSE_OUTPUT_KEY,
    LEGACY_OUTPUT_KEY,
    output_location_key,
)
from facts_experiment_builder.application.setup_experiment import (
    finalize_experiment_setup,
    prepare_experiment_setup,
)
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.io.experiment_repository import (
    StorageExperimentRepository,
)
from facts_experiment_builder.io.paths import ExperimentPaths
from tests.unit.helpers import InMemoryModuleDefinitions, make_schema

_EXPERIMENT_NAME = "experiments/output_test"
_MODULE = "fair-temperature"

# ---------------------------------------------------------------------------
# output_location_key()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", [COMPOSE_OUTPUT_KEY, APPTAINER_OUTPUT_KEY])
def test_each_command_reads_its_own_key(key):
    metadata = {COMPOSE_OUTPUT_KEY: "/c", APPTAINER_OUTPUT_KEY: "/a"}
    assert output_location_key(metadata, key) == key


def test_compose_falls_back_to_deprecated_key_with_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        key = output_location_key({LEGACY_OUTPUT_KEY: "/old"}, COMPOSE_OUTPUT_KEY)
    assert key == LEGACY_OUTPUT_KEY
    assert "deprecated" in caplog.text
    assert COMPOSE_OUTPUT_KEY in caplog.text


def test_compose_key_wins_over_deprecated_key_without_a_warning(caplog):
    metadata = {COMPOSE_OUTPUT_KEY: "/new", LEGACY_OUTPUT_KEY: "/old"}
    with caplog.at_level(logging.WARNING):
        key = output_location_key(metadata, COMPOSE_OUTPUT_KEY)
    assert key == COMPOSE_OUTPUT_KEY
    assert caplog.text == ""


def test_apptainer_does_not_fall_back_to_deprecated_key():
    with pytest.raises(ValueError, match=APPTAINER_OUTPUT_KEY):
        output_location_key({LEGACY_OUTPUT_KEY: "/old"}, APPTAINER_OUTPUT_KEY)


@pytest.mark.parametrize("key", [COMPOSE_OUTPUT_KEY, APPTAINER_OUTPUT_KEY])
def test_missing_key_raises_value_error_naming_it(key):
    with pytest.raises(ValueError, match=key):
        output_location_key({}, key)


# ---------------------------------------------------------------------------
# setup-experiment, then generate-compose / generate-apptainer
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path) -> Path:
    workspace_dir = tmp_path / "workspace"
    (workspace_dir / "experiments").mkdir(parents=True)
    return workspace_dir


def _experiment_paths(workspace: Path) -> ExperimentPaths:
    return ExperimentPaths(
        workspace_dir=workspace,
        experiment_name=ExperimentName.parse(_EXPERIMENT_NAME),
    )


def _registry() -> InMemoryModuleDefinitions:
    # Every module has an argument: the Apptainer template needs at least one per
    # service.
    scenario_arg = {"name": "scenario", "type": "str", "source": "metadata.scenario"}
    return InMemoryModuleDefinitions(
        {
            name: make_schema(name, arguments={"top_level": [scenario_arg]})
            for name in ("fair-temperature", "tlm-sterodynamics", "facts-total")
        }
    )


def _set_up(workspace: Path) -> Path:
    """Run setup-experiment, then fill in the required values a user adds by hand."""
    prepared = prepare_experiment_setup(
        experiment_name=_EXPERIMENT_NAME,
        module_regions=None,
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step="tlm-sterodynamics",
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step=None,
        workspace_dir=workspace,
    )
    config_path = finalize_experiment_setup(
        experiment_name=_EXPERIMENT_NAME,
        experiment_paths=prepared.experiment_paths,
        experiment_skeleton=prepared.experiment_skeleton,
        workflows_dict={"all-modules": "tlm-sterodynamics"},
        pipeline_id="abc123",
        scenario="ssp585",
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
    _edit_config(
        config_path,
        **{
            "pipeline-id": "abc123",
            "nsamps": 50,
            "baseyear": 2005,
            "pyear_start": 2020,
            "pyear_end": 2150,
            "pyear_step": 10,
        },
    )
    return config_path


def _edit_config(config_path: Path, **changes) -> None:
    """Set (or, with None, remove) top-level keys, as a user editing the file would."""
    config = yaml.safe_load(config_path.read_text())
    for key, value in changes.items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))


def _compose(workspace: Path) -> None:
    generate_compose(
        experiment_name=_EXPERIMENT_NAME,
        workspace_dir=workspace,
        experiment_repo=StorageExperimentRepository(),
    )


def _apptainer_script(workspace: Path) -> str:
    output = generate_apptainer(
        experiment_name=_EXPERIMENT_NAME,
        workspace_dir=workspace,
        experiment_repo=StorageExperimentRepository(),
    )
    return output.script_path.read_text()


def test_generate_commands_use_setup_defaults(workspace):
    _set_up(workspace)
    paths = _experiment_paths(workspace)

    _compose(workspace)
    script = _apptainer_script(workspace)

    # Module output dirs are created under each command's output location.
    assert (paths.compose_output_dir / _MODULE).is_dir()
    assert f'OUTPUT_DIR="{paths.apptainer_output_dir}"' in script


def test_generate_commands_use_edited_locations_as_written(workspace, tmp_path):
    config_path = _set_up(workspace)
    compose_out = tmp_path / "elsewhere" / "compose-results"
    apptainer_out = tmp_path / "elsewhere" / "apptainer-results"
    _edit_config(
        config_path,
        **{
            COMPOSE_OUTPUT_KEY: str(compose_out),
            APPTAINER_OUTPUT_KEY: str(apptainer_out),
        },
    )

    _compose(workspace)
    script = _apptainer_script(workspace)

    assert (compose_out / _MODULE).is_dir()
    assert f'OUTPUT_DIR="{apptainer_out}"' in script
    paths = _experiment_paths(workspace)
    assert not paths.compose_output_dir.exists()
    assert not paths.apptainer_output_dir.exists()


def test_compose_reads_deprecated_key_from_an_old_config(workspace, tmp_path, caplog):
    config_path = _set_up(workspace)
    old_output = tmp_path / "old-style-output"
    _edit_config(
        config_path,
        **{COMPOSE_OUTPUT_KEY: None, LEGACY_OUTPUT_KEY: str(old_output)},
    )

    with caplog.at_level(logging.WARNING):
        _compose(workspace)

    assert (old_output / _MODULE).is_dir()
    assert "deprecated" in caplog.text


def test_apptainer_without_its_key_raises(workspace):
    config_path = _set_up(workspace)
    _edit_config(config_path, **{APPTAINER_OUTPUT_KEY: None})

    with pytest.raises(ValueError, match=APPTAINER_OUTPUT_KEY):
        _apptainer_script(workspace)
