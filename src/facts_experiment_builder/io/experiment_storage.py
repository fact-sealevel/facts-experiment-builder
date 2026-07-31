from facts_experiment_builder.core.experiment.paths import (
    ExperimentPathContainer,
)


def make_output_dir(experiment_paths: ExperimentPathContainer) -> None:
    output_dir = experiment_paths.output_dir
    output_dir.mkdir(parents=True)
