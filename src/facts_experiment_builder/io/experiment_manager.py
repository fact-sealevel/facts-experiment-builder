from pathlib import Path


def make_experiment_metadata_path_from_experiment_dir(experiment_path: Path) -> Path:
    return experiment_path / "experiment-config.yaml"


def experiment_metadata_file_exists(experiment_metadata_path: Path) -> None:
    if not experiment_metadata_path.exists():
        raise FileNotFoundError(
            f"Experiment metadata file not found at {experiment_metadata_path}"
        )
