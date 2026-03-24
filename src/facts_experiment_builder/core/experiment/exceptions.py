class ExperimentAlreadyExistsError(Exception):
    def __init__(self, experiment_name: str, path: str):
        self.experiment_name = experiment_name
        self.path = path
        super().__init__(
            f"Experiment '{experiment_name}' already exists at path {path}. "
            "To start fresh, delete the existing directory or choose a different name."
        )
