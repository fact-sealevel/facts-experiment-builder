from facts_experiment_builder.infra.experiment_storage import (
    FileSystemExperimentStorage,
    ExperimentParentNotFoundError,
    ExperimentRootNotFoundError,
)
from pathlib import Path
from facts_experiment_builder.core.experiment.name import ExperimentName
import pytest


def test_missing_parent_raises_correct_error(tmp_path):
    storage = FileSystemExperimentStorage(tmp_path)
    exp = ExperimentName.parse("fake_dir/new_experiment")

    with pytest.raises(ExperimentParentNotFoundError):
        storage.create(exp=exp)


def test_missing_root_raises_correct_error(tmp_path):
    root = Path(tmp_path, "fake_dir").resolve()
    with pytest.raises(ExperimentRootNotFoundError):
        FileSystemExperimentStorage(root)
