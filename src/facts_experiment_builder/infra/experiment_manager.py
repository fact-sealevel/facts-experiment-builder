from pathlib import Path
from typing import Optional


def make_experiment_path_from_experiment_name(
    experiment_name: str,
    project_root: Path = None,
) -> Path:
    if project_root is None:
        project_root = Path.cwd()

    experiment_directory = project_root / experiment_name
    return experiment_directory


def make_experiment_metadata_path_from_experiment_dir(experiment_path: Path) -> Path:
    return experiment_path / "experiment-config.yaml"


def experiment_directory_exists(
    experiment_directory: Path,
) -> bool:
    return experiment_directory.exists()


def experiment_metadata_file_exists(experiment_metadata_path: Path) -> None:
    if not experiment_metadata_path.exists():
        raise FileNotFoundError(
            f"Experiment metadata file not found at {experiment_metadata_path}"
        )


def create_experiment_directory(
    experiment_directory: Path,
) -> None:
    experiment_directory.mkdir(parents=True)


def create_experiment_directory_files(
    experiment_directory: Path,
    # module_names: List[str],
) -> None:
    data_dir = experiment_directory / "output"
    data_dir.mkdir(parents=True)
    # if module_names:
    #    for name in module_names:
    #        (data_dir / name).mkdir(parents=True)


def use_custom_output_path(custom_output_path: Optional[Path] = None) -> bool:
    if custom_output_path is not None:
        return True
    else:
        return False


def resolve_default_experiment_compose_path(
    experiment_path: Path,
) -> Path:
    assert not experiment_path.as_posix().endswith(".yaml"), (
        f"Expected path to directory, received : {experiment_path}"
    )

    output_path = experiment_path / "experiment-compose.yaml"

    return output_path


def resolve_custom_experiment_compose_path(
    custom_output_path: Optional[Path] = None,
) -> Path:
    assert custom_output_path is not None, (
        f"Expected valid custom output path, received {custom_output_path}"
    )
    output_path = Path(custom_output_path).resolve(strict=True)

    return output_path


def resolve_experiment_parent_dir(experiment_name: str) -> Path:
    experiment_name_as_path = Path(experiment_name)
    parent_path = experiment_name_as_path.parent
    return parent_path.resolve(strict=True)
