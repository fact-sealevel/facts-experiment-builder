#!/usr/bin/env python3
"""Generate Docker Compose file from experiment config."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from facts_experiment_builder.application.execution_plan import (
    _ExecutionPlan,
    _collect_workflow_output_paths_by_type,  # noqa: F401 — re-exported for tests
)
from facts_experiment_builder.application.prepare_plan import prepare_execution_plan
from facts_experiment_builder.application.storage import (
    ExperimentRepository,
)
from facts_experiment_builder.core.experiment.name import ExperimentName
from facts_experiment_builder.core.module.module_service_path_resolution import (
    resolve_experiment_data_paths,
)
from facts_experiment_builder.io.paths import ExperimentPaths

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SUCCESS = 25  # custom level between INFO (20) and WARNING (30); must match CLI handler

_REQUIRED_FIELDS = [
    "experiment_name",
    "pipeline-id",
    "nsamps",
    "scenario",
    "pyear_start",
    "pyear_end",
    "pyear_step",
    "baseyear",
    "module-specific-input-data",
    "shared-input-data",
    "output-data-location",
]


@dataclass(frozen=True)
class PrepareComposeOutput:
    compose_dict: dict
    compose_path: Path


def _log_success(msg: str, *args: object) -> None:
    logger.log(_SUCCESS, msg, *args)


def check_metadata_has_required_fields(metadata_obj, required_fields):
    """This function accepts a list of required fields and a metadata object and subsets
    the metadata to required fields."""
    # Subset
    required_fields_meta = {
        k: v for k, v in metadata_obj.items() if k in required_fields
    }

    # R aise error if any are missing a value
    for k, v in required_fields_meta.items():
        if v is None:
            raise ValueError(
                f"A value for {k} is required but none was found. Check that all required fields in this experiment's experiment-config.yml have been completed."
            )


def render_compose_services(execution_plan: _ExecutionPlan) -> dict[str, Any]:
    """Render an _ExecutionPlan into Docker Compose service dicts."""
    services: dict[str, Any] = {}

    for service_name, spec in execution_plan.standard_specs.items():
        services[service_name] = spec.generate_compose_service(
            climate_service_name=execution_plan.climate_service_name,
            suppress_output_types=execution_plan.suppress_output_types,
        )

    for service_name, (spec, wf) in execution_plan.facts_total_specs.items():
        compose_svc = spec.generate_compose_service()
        compose_svc["depends_on"] = {
            mod: {"condition": "service_completed_successfully"}
            for mod in wf.module_names
        }
        services[service_name] = compose_svc
        _log_success("Created %s workflow service", service_name)

    for service_name, (spec, depends_on_service) in execution_plan.esl_specs.items():
        compose_svc = spec.generate_compose_service()
        compose_svc["depends_on"] = {
            depends_on_service: {"condition": "service_completed_successfully"}
        }
        services[service_name] = compose_svc
        _log_success("Created %s ESL workflow service", service_name)

    return services


def generate_compose(
    experiment_name: str,
    workspace_dir: Path,
    experiment_repo: ExperimentRepository,
    custom_compose_path: Path | None = None,
) -> PrepareComposeOutput:
    """Generate the Docker Compose dict for an experiment.

    Args:
        experiment_name: Name of the experiment (path relative to workspace_dir)
        workspace_dir: Workspace containing the experiment directory
        experiment_repo: Repository used to load experiment-config.yaml
        custom_compose_path: Optional path to write the compose file to instead of the
            default location

    Returns:
        PrepareComposeOutput with the compose dict and the path to write it to
    """
    # TODO: in future, should probably make a dataclass or similar for experiment metadata dict so that
    # can just access an attr instead of needing fns to get names from manifest etc?

    experiment_name_obj = ExperimentName.parse(raw_name=experiment_name)

    experiment_paths = ExperimentPaths(
        workspace_dir=workspace_dir,
        experiment_name=experiment_name_obj,
    )
    # experiment_paths.custom_compose_path = custom_compose_path

    # handle custom compose, if passed -- is this still necessary?
    compose_path = (
        custom_compose_path.resolve()
        if custom_compose_path is not None
        else experiment_paths.compose_path
    )
    experiment_dir = experiment_paths.config_path.parent

    # Check that paths are valid
    assert experiment_dir.is_dir(), (
        f"Expected 'experiment_dir.is_dir() is True', received: {experiment_dir.is_dir()}."
    )
    config_path = experiment_paths.config_path
    assert config_path.exists(), (
        f"Did not find `experiment-config.yaml` at '{config_path}'. Please ensure correct path/experiment name."
    )

    # log message to send to CLI
    logger.info(
        "Found experiment config file at provided path", extra={"detail": config_path}
    )

    metadata_dict = experiment_repo.get(
        config_path=config_path,
    )

    data_paths = resolve_experiment_data_paths(metadata_dict)
    _plan, execution_plan = prepare_execution_plan(metadata_dict, data_paths)

    services = render_compose_services(execution_plan)
    output_obj = PrepareComposeOutput(
        compose_dict={"services": services}, compose_path=compose_path
    )
    return output_obj
