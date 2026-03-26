import pytest


## shared fixtures
@pytest.fixture
def experiment_name():
    input = "integration_test_experiment"
    return input


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / "experiments").mkdir()
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
def totaling_step():
    """The module to include in the totaling step of the integration test experiment."""
    input = "facts-total"
    return input


@pytest.fixture
def extremesealevel_step():
    """The module(s) to include in the extremesealevel step of the integration test experiment."""
    input = "extremesealevel-pointsoverthreshold"
    return input


@pytest.fixture
def general_inputs_path():
    input = ("--general-inputs", "/path/to/general/inputs")
    return input


@pytest.fixture
def module_specific_inputs_path():
    input = ("--module-specific-inputs", "/path/to/module_specific/inputs")
    return input


@pytest.fixture
def setup_args(
    experiment_name,
    climate_step,
    sealevel_step,
    totaling_step,
    extremesealevel_step,
    module_specific_inputs_path,
    general_inputs_path,
):
    input = [
        "--experiment-name",
        experiment_name,
        "--pipeline-id",
        "aaa",
        "--scenario",
        "ssp585",
        "--pyear-start",
        "2020",
        "--pyear-end",
        "2150",
        "--pyear-step",
        "10",
        "--baseyear",
        "2005",
        "--seed",
        "1234",
        "--nsamps",
        "100",
        "--climate-step",
        climate_step,
        "--sealevel-step",
        sealevel_step,
        "--totaling-step",
        totaling_step,
        "--extremesealevel-step",
        extremesealevel_step,
        "--module-specific-inputs",
        module_specific_inputs_path[1],
        "--general-inputs",
        general_inputs_path[1],
    ]
    return input


## compose fixtures
@pytest.fixture
def compose_args(experiment_name):
    return ["--experiment-name", experiment_name]
