import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_SOURCE = REPO_ROOT / "facts-module-registry"


# @pytest.fixture(autouse=True)
# def registry_env(monkeypatch):
#     """Point the registry at the real source via env var for all integration tests.

#     Using FEB_MODULE_REGISTRY_DIR bypasses the git health checks (no warnings
#     in tests) and always resolves to a stable path, so the lru_cache on
#     _get_default_registry never goes stale between test cases.
#     """
#     monkeypatch.setenv("FEB_MODULE_REGISTRY_DIR", str(REGISTRY_SOURCE))


## shared fixtures
@pytest.fixture
def experiment_name():
    input = "experiments/integration_test_experiment"
    return input


# @pytest.fixture
# def project_root(tmp_path):
#     if not REGISTRY_SOURCE.exists():
#         pytest.skip(
#             "facts-module-registry not present — clone it to run integration tests"
#         )
#     (tmp_path / "experiments").mkdir()
#     return tmp_path


@pytest.fixture
def module_registry(tmp_path):
    """fake path to module registry to use for testing."""
    registry = Path(tmp_path / "fake_registry")
    return registry


@pytest.fixture
def project_root(tmp_path):
    """fake proejct root to use for testing"""
    project_root = Path(tmp_path, "workspace")
    return project_root


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
    input = ("--shared-input-data", "/path/to/general/inputs")
    return input


@pytest.fixture
def module_specific_inputs_path():
    input = ("--module-specific-input-data", "/path/to/module_specific/inputs")
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
    project_root,
    module_registry,
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
        "--module-specific-input-data",
        module_specific_inputs_path[1],
        "--shared-input-data",
        shared_inputs_path[1],
        "--root",
        project_root,
        "--module-registry",
        module_registry,
    ]
    return input


## compose fixtures
@pytest.fixture
def compose_args(experiment_name):
    return ["--experiment-name", experiment_name]
