import pytest
from pathlib import Path
import click

TEST_DATA = Path(__file__).parent / "data"


## shared fixtures
@pytest.fixture
def experiment_name():
    name = "test_experiments/integration_test_experiment1"
    return name


@pytest.fixture
def module_registry(tmp_path):
    """fake path to module registry to use for testing."""
    registry = Path(tmp_path / "fake_registry")
    registry.mkdir()

    yaml_src = TEST_DATA / "example_module_registry_entry.yaml"
    # make directory for a module that resembles registry structure
    module = Path(registry, "fake-name")
    module.mkdir(parents=True)

    # make minimal fake yaml
    (module / "fake-name_module.yaml").write_text(yaml_src.read_text())

    return registry


@pytest.fixture
def project_root(tmp_path):
    """fake proejct root to use for testing"""
    path = Path(tmp_path, "workspace")
    path.mkdir()
    return path


## setup new experiment fixtures
@pytest.fixture
def climate_step():
    """The module to include in the temperature step of the integration test experiment."""
    name = "fair-temperature"
    return name


@pytest.fixture
def sealevel_step():
    """The module(s) to include in the sea-level step of the integration test experiment."""
    names = (
        "bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,"
        "ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,"
        "nzinsargps-verticallandmotion,kopp14-verticallandmotion"
    )
    return names


@pytest.fixture
def extremesealevel_step():
    """The module(s) to include in the extremesealevel step of the integration test experiment."""
    name = "extremesealevel-pointsoverthreshold"
    return name


@pytest.fixture
def shared_inputs_path():
    name = ("--shared-input-data", "/path/to/general/inputs")
    return name


@pytest.fixture
def module_specific_inputs_path():
    name = ("--module-specific-input-data", "/path/to/module_specific/inputs")
    return name


@pytest.fixture
def scenario():
    scenario = "ssp585"
    return scenario


@pytest.fixture
def pyear_start():
    year = 2020
    return year


@pytest.fixture
def pyear_end():
    year = 2150
    return year


@pytest.fixture
def pyear_step():
    year = 10
    return year


@pytest.fixture
def baseyear():
    year = 2005
    return year


@pytest.fixture
def nsamps():
    num = 100
    return num


@pytest.fixture
def pipeline_id():
    name = "aaa"
    return name


@pytest.fixture
def decline_extra_prompts(monkeypatch):
    """Automatically decline any click.confirm prompts"""

    def _unexpected(*a, **k):
        raise AssertionError(f"Unexpected click.prompt call: {a} {k}")

    monkeypatch.setattr(click, "prompt", _unexpected)
    monkeypatch.setattr(click, "confirm", lambda *a, **k: False)


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
    tmp_path,
    decline_extra_prompts,
):
    # Make fake registry dir, root
    fake_registry = Path(tmp_path, module_registry)

    # Make dir for parent dir in expeirment name
    # parent_exp_dir = Path(tmp_path, experiment_name).parent

    # write empty yaml files for all modules
    def make_fake_module_yaml(module_name: str, fake_registry: Path) -> None:
        module_yaml_path = (
            fake_registry / module_name.replace("_", "-") / f"{module_name}_module.yaml"
        )
        module_yaml_path.parent.mkdir(parents=True, exist_ok=True)

        module_yaml_path.touch()

    module_list = [
        "fair-temperature",
        "bamber19-icesheets",
        "deconto21-ais",
        "fittedismip-gris",
        "larmip-ais",
        "ipccar5-glaciers",
        "ipccar5-icesheets",
        "tlm-sterodynamics",
        "nzinsargps-verticallandmotion",
        "kopp14-verticallandmotion",
        "extremesealevel-pointsoverthreshold",
        "facts-total",
    ]
    module_list = [m.replace("-", "_") for m in module_list]

    for module in module_list:
        make_fake_module_yaml(module, fake_registry=fake_registry)

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
        fake_registry,
    ]
    return input


## compose fixtures
@pytest.fixture
def compose_args(experiment_name):
    return ["--experiment-name", experiment_name]
