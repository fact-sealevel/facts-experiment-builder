from facts_experiment_builder.core.experiment import FactsExperiment
from pathlib import Path
from typing import Optional, List
from facts_experiment_builder.infra.path_manager import find_project_root

def resolve_experiment_directory_path(
    experiment_name: str,
    project_root: Path = None,
    ) -> Path:

    if project_root is None:
        project_root = find_project_root()
    
    experiment_directory = project_root / "experiments" / experiment_name
    return experiment_directory

def check_if_experiment_directory_exists(
    experiment_directory: Path,
    ) -> bool:
    return experiment_directory.exists()

def create_experiment_directory(
    experiment_directory: Path,
    ) -> None:
    experiment_directory.mkdir(parents=True)

def create_experiment_directory_files(
    experiment_directory: Path,
    module_names: List[str],
    ) -> None:
    data_dir = experiment_directory / "data" / "output"
    data_dir.mkdir(parents=True)
    if module_names:
        for name in module_names:
            (data_dir / name).mkdir(parents=True)
    print(f"✓ Created data/output directory")