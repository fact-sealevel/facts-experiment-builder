from pathlib import Path

from facts_experiment_builder.core.experiment.name import ExperimentName


class ExperimentSetupError(Exception):
    """Base class for errors that prevent creating a new experiment."""


class ExperimentParentNotFoundError(ExperimentSetupError):
    def __init__(self, experiment_name: ExperimentName, workspace_dir: Path):
        self.experiment_name = experiment_name
        self.workspace_dir = workspace_dir
        super().__init__(
            f"Cannot create experiment '{experiment_name}': parent directory "
            f"'{experiment_name.parent}' does not exist under workspace "
            f"'{workspace_dir}'. Create it first or choose a different name."
        )


class ExperimentOutsideWorkspaceError(ExperimentSetupError):
    def __init__(
        self, experiment_name: ExperimentName, target: Path, workspace_dir: Path
    ):
        self.experiment_name = experiment_name
        self.target = target
        self.workspace_dir = workspace_dir
        super().__init__(
            f"Cannot create experiment '{experiment_name}': it resolves to "
            f"'{target}', which is outside workspace '{workspace_dir}'."
        )


class ExperimentAlreadyExistsError(ExperimentSetupError):
    def __init__(
        self,
        # experiment_name: str,
        path: str,
    ):
        # self.experiment_name = experiment_name
        self.path = path
        super().__init__(
            f"Experiment already exists at path {path}. "
            # f"Experiment '{experiment_name}' already exists at path {path}. "
            "To start fresh, delete the existing directory or choose a different name."
        )
