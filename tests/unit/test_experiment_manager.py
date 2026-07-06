from facts_experiment_builder.infra.experiment_manager import (
    resolve_experiment_directory_path,
)

EXAMPLE_EXPERIMENT_NAME = "facts-experiment-testing"


def test_resolve_experiment_directory_path_places_dir_inside_experiments(
    experiment_name=EXAMPLE_EXPERIMENT_NAME,
):
    experiment_dir = resolve_experiment_directory_path(experiment_name=experiment_name)
    assert experiment_dir.parent.name == "experiments"
