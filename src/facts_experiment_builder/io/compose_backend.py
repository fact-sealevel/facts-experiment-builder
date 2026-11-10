"""ComposeBackend: ExecutionBackend adapter that writes a Docker Compose YAML file."""

import logging
from pathlib import Path
from typing import Any

from facts_experiment_builder.application.backend import RunInfo
from facts_experiment_builder.application.log_levels import SUCCESS
from facts_experiment_builder.application.execution_graph import (
    ExecutionGraph,
    Stage,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.io.compose_service import to_compose_service
from facts_experiment_builder.io.paths import ExperimentPaths
from facts_experiment_builder.io.write_compose import (
    make_compose_yaml,
    write_compose_yaml,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# facts-total and ESL services always get a depends_on key, even when empty (a workflow
# with no modules); to_compose_service() would drop an empty one.
_ALWAYS_DEPENDS_ON = {Stage.TOTALING, Stage.EXTREME_SEALEVEL}


def _log_success(msg: str, *args: object) -> None:
    logger.log(SUCCESS, msg, *args)


def render_compose_services(graph: ExecutionGraph) -> dict[str, Any]:
    """Render an ExecutionGraph into Docker Compose service dicts."""
    services: dict[str, Any] = {}

    for service_name, node in graph.nodes.items():
        if node.stage not in _ALWAYS_DEPENDS_ON:
            services[service_name] = to_compose_service(node.run, node.depends_on)
            continue

        compose_svc = to_compose_service(node.run)
        compose_svc["depends_on"] = {
            dep.service: {"condition": "service_completed_successfully"}
            for dep in node.depends_on
        }
        services[service_name] = compose_svc
        if node.stage is Stage.TOTALING:
            _log_success("Created %s workflow service", service_name)
        else:
            _log_success("Created %s ESL workflow service", service_name)

    return services


class ComposeBackend:
    """Writes the experiment as a Docker Compose file."""

    def default_output_path(self, experiment_paths: ExperimentPaths) -> Path:
        return experiment_paths.compose_path

    def data_paths(
        self, data_paths: ExperimentDataPaths, experiment_paths: ExperimentPaths
    ) -> ExperimentDataPaths:
        return data_paths

    def render(self, graph: ExecutionGraph, info: RunInfo) -> str:
        return make_compose_yaml(
            content_dict={"services": render_compose_services(graph)}
        )

    def write(self, content: str, path: Path) -> None:
        write_compose_yaml(compose_content=content, compose_path=path)
