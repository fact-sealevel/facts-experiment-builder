from facts_experiment_builder.io.layout import (
    ExperimentPaths,
)


def make_output_dir(experiment_paths: ExperimentPaths) -> None:
    output_dir = experiment_paths.output_dir
    output_dir.mkdir(parents=True)
