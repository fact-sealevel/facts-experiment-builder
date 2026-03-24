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
def temperature_module():
    input = "fair-temperature"
    return input


@pytest.fixture
def sealevel_modules():
    input = (
        "bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,"
        "ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,"
        "nzinsargps-verticallandmotion,kopp14-verticallandmotion"
    )
    return input


@pytest.fixture
def framework_module():
    input = "facts-total"
    return input


@pytest.fixture
def extremesealevel_module():
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
    temperature_module,
    sealevel_modules,
    framework_module,
    extremesealevel_module,
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
        "--temperature-module",
        temperature_module,
        "--sealevel-modules",
        sealevel_modules,
        "--framework-module",
        framework_module,
        "--extremesealevel-module",
        extremesealevel_module,
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
