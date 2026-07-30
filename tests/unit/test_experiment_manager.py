from facts_experiment_builder.io.experiment_manager import (
    make_experiment_metadata_path_from_experiment_dir,
    experiment_metadata_file_exists,
)
import pytest


def test_make_experiment_metadata_path_from_experiment_dir_returns_correct(tmp_path):
    experiment_path = tmp_path / "experiments/experiment_name"
    result = make_experiment_metadata_path_from_experiment_dir(
        experiment_path=experiment_path
    )
    assert result == experiment_path / "experiment-config.yaml"


def test_experiment_metadata_file_exists_raises_error_when_no_file(tmp_path):
    experiment_dir_path = tmp_path / "experiments/experiment_name"
    experiment_dir_path.mkdir(parents=True)
    experiment_metadata_path = experiment_dir_path / "experiment-config.yaml"

    with pytest.raises(FileNotFoundError):
        experiment_metadata_file_exists(
            experiment_metadata_path=experiment_metadata_path
        )


def test_experiment_metadata_file_exists_runs_silently_when_file_present(tmp_path):
    experiment_dir_path = tmp_path / "experiments/experiment_name"
    experiment_dir_path.mkdir(parents=True)
    experiment_metadata_path = experiment_dir_path / "experiment-config.yaml"
    experiment_metadata_path.touch()
    experiment_metadata_file_exists(experiment_metadata_path=experiment_metadata_path)
