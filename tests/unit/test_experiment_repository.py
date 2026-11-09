from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.io.experiment_repository import (
    load_experiment_config,
)


def test_load_experiment_config_returns_dict(tmp_path):
    # Create a temporary YAML file for testing
    test_yaml_content = """
    experiment_name: test_experiment
    top_level_params:
      param1: value1
      param2: value2
    """
    test_yaml_path = tmp_path / "test_experiment_config.yaml"
    test_yaml_path.write_text(test_yaml_content)

    # Load the experiment config using the function
    loaded_config = load_experiment_config(test_yaml_path)

    # Assert that the loaded config is a dictionary and has expected keys
    assert isinstance(loaded_config, dict)
    assert loaded_config["experiment_name"] == "test_experiment"
    assert loaded_config["top_level_params"]["param1"] == "value1"
    assert loaded_config["top_level_params"]["param2"] == "value2"


def test_storage_exp_repo_get_returns_loaded_config(tmp_path):
    # Create a temporary YAML file for testing
    test_yaml_content = """
    experiment_name: test_experiment
    pipeline-id: abc123
    nsamps: 100
    scenario: ssp585
    baseyear: 2005
    pyear_start: 2020
    pyear_end: 2150
    pyear_step: 10
    module-specific-input-data: /in/module
    shared-input-data: /in/shared
    output-data-location: /out
    top_level_params:
      param1: value1
      param2: value2
    """
    test_yaml_path = tmp_path / "test_experiment_config.yaml"
    test_yaml_path.write_text(test_yaml_content)

    # Use the StorageExperimentRepository to get the config
    from facts_experiment_builder.io.experiment_repository import (
        StorageExperimentRepository,
    )

    repo = StorageExperimentRepository()
    loaded_config = repo.get(test_yaml_path)

    assert isinstance(loaded_config, LoadedExperimentConfig)
    assert loaded_config.experiment_name == "test_experiment"
    # Keys without a typed field are still available on raw.
    assert loaded_config.raw["top_level_params"]["param1"] == "value1"
    assert loaded_config.raw["top_level_params"]["param2"] == "value2"
