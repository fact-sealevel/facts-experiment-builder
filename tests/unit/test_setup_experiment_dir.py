"""Tests for experiment directory creation and the checks run at setup.

An experiment exists if its experiment-config.yaml exists. Setup never creates
parent directories (they must already exist in the workspace), refuses experiment
paths that resolve outside the workspace, and creates only the experiment directory
(not an output/ directory) right before writing the config.
"""

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from facts_experiment_builder.application.setup_experiment import (
    finalize_experiment_setup,
    prepare_experiment_setup,
)
from facts_experiment_builder.cli.setup_experiment_cli import main
from facts_experiment_builder.core.experiment.exceptions import (
    ExperimentAlreadyExistsError,
    ExperimentOutsideWorkspaceError,
    ExperimentParentNotFoundError,
)
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.io.experiment_repository import (
    StorageExperimentRepository,
)
from facts_experiment_builder.io.paths import (
    ExperimentPaths,
    check_experiment_does_not_exist,
    check_experiment_location,
    create_experiment_dir,
)
from tests.unit.helpers import InMemoryModuleDefinitions, make_schema

_EXPERIMENT_NAME = "experiments/my_experiment"


@pytest.fixture
def workspace(tmp_path) -> Path:
    """A workspace with an experiments/ parent directory, as `feb init` creates."""
    workspace_dir = tmp_path / "workspace"
    (workspace_dir / "experiments").mkdir(parents=True)
    return workspace_dir


def _paths(workspace_dir: Path, name: str = _EXPERIMENT_NAME) -> ExperimentPaths:
    return ExperimentPaths(
        workspace_dir=workspace_dir, experiment_name=ExperimentName.parse(name)
    )


def _prepare(workspace_dir: Path, name: str = _EXPERIMENT_NAME):
    return prepare_experiment_setup(
        experiment_name=name,
        module_regions=None,
        climate_step="fair-temperature",
        supplied_climate_step_data=None,
        sealevel_step="tlm-sterodynamics",
        supplied_totaled_sealevel_step_data=None,
        extremesealevel_step=None,
        workspace_dir=workspace_dir,
    )


def _finalize(prepared, name: str = _EXPERIMENT_NAME) -> Path:
    definitions = InMemoryModuleDefinitions(
        {
            "fair-temperature": make_schema("fair-temperature"),
            "tlm-sterodynamics": make_schema(
                "tlm-sterodynamics", uses_climate_file=True
            ),
            "facts-total": make_schema("facts-total"),
        }
    )
    return finalize_experiment_setup(
        experiment_name=name,
        experiment_paths=prepared.experiment_paths,
        experiment_skeleton=prepared.experiment_skeleton,
        workflows_dict={},
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
        module_registry=definitions,
        experiment_repo=StorageExperimentRepository(),
    )


def _cli_args(workspace_dir: Path, registry: Path, name: str = _EXPERIMENT_NAME):
    return [
        "--experiment-name",
        name,
        "--climate-step",
        "fair-temperature",
        "--sealevel-step",
        "ipccar5-icesheets",
        "--workspace-dir",
        str(workspace_dir),
        "--module-registry",
        str(registry),
    ]


def _cli_registry(fake_registry) -> Path:
    return fake_registry(
        {
            "fair-temperature": {"module_name": "fair-temperature"},
            "ipccar5-icesheets": {"module_name": "ipccar5-icesheets"},
            "facts-total": {"module_name": "facts-total"},
        }
    )


# ---------------------------------------------------------------------------
# io.paths: check_experiment_does_not_exist()
# ---------------------------------------------------------------------------


def test_check_exists_passes_when_experiment_dir_missing(workspace):
    check_experiment_does_not_exist(_paths(workspace))


def test_check_exists_passes_when_experiment_dir_exists_without_config(workspace):
    paths = _paths(workspace)
    paths.experiment_dir.mkdir()
    check_experiment_does_not_exist(paths)


def test_check_exists_raises_when_config_exists(workspace):
    paths = _paths(workspace)
    paths.experiment_dir.mkdir()
    paths.config_path.write_text("experiment_name: x\n")
    with pytest.raises(ExperimentAlreadyExistsError) as exc_info:
        check_experiment_does_not_exist(paths)
    assert exc_info.value.path == str(paths.experiment_dir)


# ---------------------------------------------------------------------------
# io.paths: check_experiment_location() / create_experiment_dir()
# ---------------------------------------------------------------------------


def test_check_location_passes_for_name_without_parent(workspace):
    check_experiment_location(_paths(workspace, "my_experiment"))


def test_check_location_raises_when_parent_missing(workspace):
    with pytest.raises(ExperimentParentNotFoundError) as exc_info:
        check_experiment_location(_paths(workspace, "funky_experiments/my_experiment"))
    assert "funky_experiments" in str(exc_info.value)


def test_check_location_raises_when_symlinked_parent_points_outside_workspace(
    workspace, tmp_path
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ExperimentOutsideWorkspaceError):
        check_experiment_location(_paths(workspace, "linked/my_experiment"))


def test_check_location_passes_when_symlinked_parent_stays_inside_workspace(
    workspace,
):
    (workspace / "alias").symlink_to(
        workspace / "experiments", target_is_directory=True
    )
    check_experiment_location(_paths(workspace, "alias/my_experiment"))


def test_create_experiment_dir_creates_dir_under_existing_parent(workspace):
    paths = _paths(workspace)
    create_experiment_dir(paths)
    assert paths.experiment_dir.is_dir()


def test_create_experiment_dir_does_not_create_missing_parent(workspace):
    paths = _paths(workspace, "funky_experiments/my_experiment")
    with pytest.raises(ExperimentParentNotFoundError):
        create_experiment_dir(paths)
    assert not (workspace / "funky_experiments").exists()


def test_create_experiment_dir_does_not_create_outside_workspace(workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ExperimentOutsideWorkspaceError):
        create_experiment_dir(_paths(workspace, "linked/my_experiment"))
    assert not (outside / "my_experiment").exists()


def test_create_experiment_dir_is_idempotent(workspace):
    paths = _paths(workspace)
    create_experiment_dir(paths)
    create_experiment_dir(paths)
    assert paths.experiment_dir.is_dir()


def test_create_experiment_dir_does_not_create_output_dir(workspace):
    paths = _paths(workspace)
    create_experiment_dir(paths)
    assert not paths.output_dir.exists()


# ---------------------------------------------------------------------------
# prepare_experiment_setup() / finalize_experiment_setup()
# ---------------------------------------------------------------------------


def test_prepare_creates_no_directories(workspace):
    prepared = _prepare(workspace)
    assert not prepared.experiment_paths.experiment_dir.exists()


def test_prepare_raises_when_parent_missing_and_creates_nothing(workspace):
    with pytest.raises(ExperimentParentNotFoundError):
        _prepare(workspace, "funky_experiments/my_experiment")
    assert not (workspace / "funky_experiments").exists()


def test_prepare_raises_when_config_exists(workspace):
    paths = _paths(workspace)
    paths.experiment_dir.mkdir()
    paths.config_path.write_text("experiment_name: x\n")
    with pytest.raises(ExperimentAlreadyExistsError):
        _prepare(workspace)


def test_setup_writes_config_into_new_experiment_dir(workspace):
    config_path = _finalize(_prepare(workspace))
    assert config_path == _paths(workspace).config_path
    assert config_path.is_file()


def test_setup_without_parent_dir_creates_experiment_in_workspace(workspace):
    name = "my_experiment"
    config_path = _finalize(_prepare(workspace, name), name)
    assert config_path == workspace / name / "experiment-config.yaml"
    assert config_path.is_file()


def test_setup_does_not_create_output_dir(workspace):
    _finalize(_prepare(workspace))
    assert not _paths(workspace).output_dir.exists()


def test_setup_default_output_data_location_is_experiment_paths_output_dir(
    workspace,
):
    config_path = _finalize(_prepare(workspace))
    config = yaml.safe_load(config_path.read_text())
    assert config["output-data-location"] == _paths(workspace).output_dir.as_posix()


def test_setup_succeeds_when_experiment_dir_exists_without_config(workspace):
    paths = _paths(workspace)
    paths.experiment_dir.mkdir()
    (paths.experiment_dir / "notes.txt").write_text("keep me\n")
    _finalize(_prepare(workspace))
    assert paths.config_path.is_file()
    assert (paths.experiment_dir / "notes.txt").read_text() == "keep me\n"


def test_setup_succeeds_when_output_dir_exists_without_config(workspace):
    """An existing output/ directory alone does not mean the experiment exists
    (previously setup failed here with FileExistsError)."""
    paths = _paths(workspace)
    paths.output_dir.mkdir(parents=True)
    _finalize(_prepare(workspace))
    assert paths.config_path.is_file()


def test_finalize_raises_and_keeps_config_created_after_prepare(workspace):
    prepared = _prepare(workspace)
    paths = prepared.experiment_paths
    paths.experiment_dir.mkdir()
    paths.config_path.write_text("experiment_name: original\n")
    with pytest.raises(ExperimentAlreadyExistsError):
        _finalize(prepared)
    assert paths.config_path.read_text() == "experiment_name: original\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_second_setup_of_same_experiment_fails_cleanly(
    workspace, fake_registry, decline_extra_prompts
):
    args = _cli_args(workspace, _cli_registry(fake_registry))
    runner = CliRunner()

    first = runner.invoke(main, args)
    assert first.exit_code == 0, f"{first.output}\n{first.exception!r}"
    config_path = _paths(workspace).config_path
    original = config_path.read_text()

    second = runner.invoke(main, args)
    assert second.exit_code == 1
    assert "already exists" in second.output
    assert not isinstance(second.exception, ExperimentAlreadyExistsError)
    assert config_path.read_text() == original


def test_cli_missing_parent_fails_cleanly_and_creates_nothing(
    workspace, fake_registry, decline_extra_prompts
):
    name = "funky_experiments/my_new_experiment"
    result = CliRunner().invoke(
        main, _cli_args(workspace, _cli_registry(fake_registry), name)
    )
    assert result.exit_code == 1
    output = " ".join(result.output.split())  # undo rich's line wrapping
    assert "parent directory 'funky_experiments' does not exist" in output
    assert not isinstance(result.exception, ExperimentParentNotFoundError)
    assert not (workspace / "funky_experiments").exists()
