#!/usr/bin/env python3
"""Generate an experiment's run file (e.g. Docker Compose YAML or an Apptainer bash
script) with a given ExecutionBackend."""

import logging
from dataclasses import dataclass
from pathlib import Path

from facts_experiment_builder.application.backend import ExecutionBackend, RunInfo
from facts_experiment_builder.application.execution_graph import build_execution_graph
from facts_experiment_builder.application.prepare_plan import prepare_execution_plan
from facts_experiment_builder.application.storage import ExperimentRepository
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.core.module.module_service_path_resolution import (
    resolve_experiment_data_paths,
)
from facts_experiment_builder.io.paths import ExperimentPaths

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class GenerateRunFileOutput:
    path: Path


def generate_run_file(
    experiment_name: str,
    workspace_dir: Path,
    experiment_repo: ExperimentRepository,
    backend: ExecutionBackend,
    custom_output_path: Path | None = None,
) -> GenerateRunFileOutput:
    """Generate and write the run file for an experiment.

    Args:
        experiment_name: Name of the experiment (path relative to workspace_dir)
        workspace_dir: Workspace containing the experiment directory
        experiment_repo: Repository used to load experiment-config.yaml
        backend: Backend that renders and writes the run file
        custom_output_path: Optional path to write the run file to instead of the
            backend's default location

    Returns:
        GenerateRunFileOutput with the path of the written file

    Raises:
        FileNotFoundError: if the experiment directory or its experiment-config.yaml
            does not exist
    """
    experiment_paths = ExperimentPaths(
        workspace_dir=workspace_dir,
        experiment_name=ExperimentName.parse(raw_name=experiment_name),
    )
    output_path = (
        custom_output_path.resolve()
        if custom_output_path is not None
        else backend.default_output_path(experiment_paths)
    )

    experiment_dir = experiment_paths.experiment_dir
    if not experiment_dir.is_dir():
        raise FileNotFoundError(
            f"Did not find experiment directory '{experiment_dir}'. "
            "Please ensure the experiment name and workspace directory are correct."
        )
    config_path = experiment_paths.config_path
    if not config_path.exists():
        raise FileNotFoundError(
            f"Did not find `experiment-config.yaml` at '{config_path}'. "
            "Please ensure the experiment name and workspace directory are correct."
        )
    logger.info(
        "Found experiment config file at provided path", extra={"detail": config_path}
    )

    config = experiment_repo.get(config_path=config_path)
    data_paths = backend.data_paths(
        resolve_experiment_data_paths(config.raw), experiment_paths
    )
    plan, execution_plan = prepare_execution_plan(config, data_paths)
    graph = build_execution_graph(execution_plan)

    content = backend.render(
        graph,
        RunInfo(
            config=config,
            data_paths=data_paths,
            workspace_dir=workspace_dir,
            workflow_names=list(plan.workflows),
        ),
    )
    backend.write(content, output_path)
    return GenerateRunFileOutput(path=output_path)
