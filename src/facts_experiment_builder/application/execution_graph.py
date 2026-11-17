"""Backend-neutral execution graph: which services run, in what order, after what.

build_execution_graph() turns an _ExecutionPlan into an ExecutionGraph. Every backend
reads the same graph: Compose uses each node's depends_on, Apptainer uses its stage and
wait_for_files.
"""

from dataclasses import dataclass
from enum import Enum

from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.core.module.module_service_spec import ModuleServiceSpec
from facts_experiment_builder.core.module.service_run import (
    ServiceDependency,
    ServiceRun,
)


class Stage(Enum):
    """Experiment step a service belongs to.

    Services in a later stage use outputs from earlier ones.
    """

    INDEPENDENT = 1  # climate module, and sea-level modules without uses_climate_file
    NEEDS_CLIMATE = 2  # sea-level modules with uses_climate_file
    TOTALING = 3  # facts-total, one per workflow × output type
    EXTREME_SEALEVEL = 4  # ESL, one per module × workflow


@dataclass(frozen=True)
class ServiceNode:
    """One service in the graph."""

    run: ServiceRun
    stage: Stage
    depends_on: list[ServiceDependency]  # services that must finish first
    wait_for_files: list[str]  # host paths to wait for (climate outputs)


@dataclass(frozen=True)
class ExecutionGraph:
    """What runs, after what, and waiting for which files.

    Read by every backend.
    """

    # service name -> node, in run order: climate, sea-level, facts-total, ESL
    nodes: dict[str, ServiceNode]
    climate_service_name: str | None

    def in_stage(self, stage: Stage) -> dict[str, ServiceNode]:
        """Nodes in `stage`, keeping run order."""
        return {name: node for name, node in self.nodes.items() if node.stage == stage}


def _climate_wait_files(spec: ModuleServiceSpec, climate: ServiceRun) -> list[str]:
    """Return host paths `spec` must wait for from the climate service's outputs.

    The climate outputs `spec` needs are named by its inputs' climate_step_output; their
    host paths come from the climate service's host_outputs.
    """
    needed = {
        inp.climate_step_output
        for inp in spec.module_definition.arguments.inputs
        if inp.climate_step_output
    }
    return [path for name, path in climate.host_outputs.items() if name in needed]


def build_execution_graph(execution_plan: _ExecutionPlan) -> ExecutionGraph:
    """Build the backend-neutral ExecutionGraph for an _ExecutionPlan.

    suppress_output_types applies to the climate and sea-level services only.
    """
    suppress = execution_plan.suppress_output_types
    climate_name = execution_plan.climate_service_name
    nodes: dict[str, ServiceNode] = {}

    # Build the climate run first so climate-dependent services can wait on its outputs.
    climate_spec = (
        execution_plan.standard_specs.get(climate_name) if climate_name else None
    )
    climate_run = (
        climate_spec.to_service_run(suppress_output_types=suppress)
        if climate_spec
        else None
    )

    for service_name, spec in execution_plan.standard_specs.items():
        depends_on = spec.dependencies(climate_service_name=climate_name)
        if climate_run is not None and service_name == climate_name:
            nodes[service_name] = ServiceNode(
                run=climate_run,
                stage=Stage.INDEPENDENT,
                depends_on=depends_on,
                wait_for_files=[],
            )
        elif not spec.module_definition.uses_climate_file:
            nodes[service_name] = ServiceNode(
                run=spec.to_service_run(suppress_output_types=suppress),
                stage=Stage.INDEPENDENT,
                depends_on=depends_on,
                wait_for_files=[],
            )
        else:
            nodes[service_name] = ServiceNode(
                run=spec.to_service_run(suppress_output_types=suppress),
                stage=Stage.NEEDS_CLIMATE,
                depends_on=depends_on,
                wait_for_files=(
                    _climate_wait_files(spec, climate_run) if climate_run else []
                ),
            )

    for service_name, (spec, wf) in execution_plan.facts_total_specs.items():
        nodes[service_name] = ServiceNode(
            run=spec.to_service_run(),
            stage=Stage.TOTALING,
            depends_on=[ServiceDependency(service=m) for m in wf.module_names],
            wait_for_files=[],
        )

    for service_name, (spec, depends_on_service) in execution_plan.esl_specs.items():
        nodes[service_name] = ServiceNode(
            run=spec.to_service_run(),
            stage=Stage.EXTREME_SEALEVEL,
            depends_on=[ServiceDependency(service=depends_on_service)],
            wait_for_files=[],
        )

    return ExecutionGraph(nodes=nodes, climate_service_name=climate_name)
