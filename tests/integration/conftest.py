import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


## shared fixtures
@pytest.fixture
def experiment_name():
    input = "integration_test_experiment"
    return input


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / "experiments").mkdir()
    (tmp_path / "facts-module-registry").symlink_to(
        REPO_ROOT / "facts-module-registry", target_is_directory=True
    )
    return tmp_path


## setup new experiment fixtures
@pytest.fixture
def climate_step():
    """The module to include in the temperature step of the integration test experiment."""
    input = "fair-temperature"
    return input


@pytest.fixture
def sealevel_step():
    """The module(s) to include in the sea-level step of the integration test experiment."""
    input = (
        "bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,"
        "ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,"
        "nzinsargps-verticallandmotion,kopp14-verticallandmotion"
    )
    return input


@pytest.fixture
def extremesealevel_step():
    """The module(s) to include in the extremesealevel step of the integration test experiment."""
    input = "extremesealevel-pointsoverthreshold"
    return input


@pytest.fixture
def shared_inputs_path():
    input = ("--shared-inputs", "/path/to/general/inputs")
    return input


@pytest.fixture
def module_specific_inputs_path():
    input = ("--module-specific-inputs", "/path/to/module_specific/inputs")
    return input


@pytest.fixture
def scenario():
    input = "ssp585"
    return input


@pytest.fixture
def pyear_start():
    input = 2020
    return input


@pytest.fixture
def pyear_end():
    input = 2150
    return input


@pytest.fixture
def pyear_step():
    input = 10
    return input


@pytest.fixture
def baseyear():
    input = 2005
    return input


@pytest.fixture
def nsamps():
    input = 100
    return input


@pytest.fixture
def pipeline_id():
    input = "aaa"
    return input


@pytest.fixture
def setup_args(
    experiment_name,
    climate_step,
    sealevel_step,
    extremesealevel_step,
    module_specific_inputs_path,
    shared_inputs_path,
    scenario,
    pyear_start,
    pyear_end,
    pyear_step,
    baseyear,
    nsamps,
    pipeline_id,
):
    input = [
        "--experiment-name",
        experiment_name,
        "--pipeline-id",
        pipeline_id,
        "--scenario",
        scenario,
        "--pyear-start",
        pyear_start,
        "--pyear-end",
        pyear_end,
        "--pyear-step",
        pyear_step,
        "--baseyear",
        baseyear,
        "--nsamps",
        nsamps,
        "--climate-step",
        climate_step,
        "--sealevel-step",
        sealevel_step,
        "--extremesealevel-step",
        extremesealevel_step,
        "--module-specific-inputs",
        module_specific_inputs_path[1],
        "--shared-inputs",
        shared_inputs_path[1],
    ]
    return input


## compose fixtures
@pytest.fixture
def compose_args(experiment_name):
    return ["--experiment-name", experiment_name]
