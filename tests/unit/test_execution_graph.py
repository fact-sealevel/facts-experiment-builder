"""Unit tests for application.execution_graph."""

import dataclasses

from facts_experiment_builder.application.execution_graph import (
    Stage,
    build_execution_graph,
)
from facts_experiment_builder.core.module.service_run import ServiceDependency
from facts_experiment_builder.core.workflow import Workflow
from tests.unit.helpers import (
    make_execution_plan,
    make_service_spec,
    make_service_spec_with_outputs,
)


def test_stage_of_each_kind_of_service():
    wf = Workflow(name="wf1", module_names=["ssp-lws", "tlm"])
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": make_service_spec("fair-temperature"),
            "ssp-lws": make_service_spec("ssp-lws"),
            "tlm": make_service_spec("tlm", uses_climate_file=True),
        },
        facts_total_specs={
            "facts-total-wf1-global": (make_service_spec("facts-total-wf1-global"), wf)
        },
        esl_specs={
            "esl-wf1": (make_service_spec("esl-wf1"), "facts-total-wf1-local"),
        },
        climate_service_name="fair-temperature",
    )
    graph = build_execution_graph(plan)

    assert {name: node.stage for name, node in graph.nodes.items()} == {
        "fair-temperature": Stage.INDEPENDENT,
        "ssp-lws": Stage.INDEPENDENT,
        "tlm": Stage.NEEDS_CLIMATE,
        "facts-total-wf1-global": Stage.TOTALING,
        "esl-wf1": Stage.EXTREME_SEALEVEL,
    }
    assert graph.climate_service_name == "fair-temperature"


def test_nodes_keep_run_order_and_in_stage_keeps_it_too():
    wf = Workflow(name="wf1", module_names=["a"])
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": make_service_spec("fair-temperature"),
            "b": make_service_spec("b", uses_climate_file=True),
            "a": make_service_spec("a"),
        },
        facts_total_specs={
            "ft-global": (make_service_spec("ft-global"), wf),
            "ft-local": (make_service_spec("ft-local"), wf),
        },
        esl_specs={"esl-wf1": (make_service_spec("esl-wf1"), "ft-local")},
        climate_service_name="fair-temperature",
    )
    graph = build_execution_graph(plan)

    assert list(graph.nodes) == [
        "fair-temperature",
        "b",
        "a",
        "ft-global",
        "ft-local",
        "esl-wf1",
    ]
    assert list(graph.in_stage(Stage.INDEPENDENT)) == ["fair-temperature", "a"]
    assert list(graph.in_stage(Stage.TOTALING)) == ["ft-global", "ft-local"]


def test_climate_dependent_service_waits_for_the_climate_output_it_declares():
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": make_service_spec_with_outputs(),
            "tlm": make_service_spec(
                "tlm", uses_climate_file=True, climate_step_output="output-gsat-file"
            ),
        },
        climate_service_name="fair-temperature",
    )
    graph = build_execution_graph(plan)

    assert graph.nodes["tlm"].wait_for_files == ["/out/fair-temperature/gsat.nc"]
    assert graph.nodes["fair-temperature"].wait_for_files == []


def test_climate_dependent_service_without_climate_module_waits_for_nothing():
    plan = make_execution_plan(
        standard_specs={
            "tlm": make_service_spec(
                "tlm", uses_climate_file=True, climate_step_output="output-gsat-file"
            ),
        },
    )
    node = build_execution_graph(plan).nodes["tlm"]

    assert node.stage is Stage.NEEDS_CLIMATE
    assert node.wait_for_files == []
    assert node.depends_on == []


def test_climate_dependent_service_depends_on_the_climate_service():
    plan = make_execution_plan(
        standard_specs={
            "fair-temperature": make_service_spec("fair-temperature"),
            "tlm": make_service_spec("tlm", uses_climate_file=True),
        },
        climate_service_name="fair-temperature",
    )
    graph = build_execution_graph(plan)

    assert graph.nodes["tlm"].depends_on == [
        ServiceDependency(service="fair-temperature")
    ]


def test_facts_total_and_esl_depend_on_their_inputs():
    wf = Workflow(name="wf1", module_names=["a", "b"])
    plan = make_execution_plan(
        facts_total_specs={"ft-local": (make_service_spec("ft-local"), wf)},
        esl_specs={"esl-wf1": (make_service_spec("esl-wf1"), "ft-local")},
    )
    graph = build_execution_graph(plan)

    assert graph.nodes["ft-local"].depends_on == [
        ServiceDependency(service="a"),
        ServiceDependency(service="b"),
    ]
    assert graph.nodes["esl-wf1"].depends_on == [ServiceDependency(service="ft-local")]


def test_suppress_output_types_applies_to_climate_and_sealevel_only():
    wf = Workflow(name="wf1", module_names=["sealevel"])
    sealevel = make_service_spec_with_outputs(module_name="sealevel")
    facts_total = make_service_spec_with_outputs(module_name="ft-global")
    plan = dataclasses.replace(
        make_execution_plan(
            standard_specs={"sealevel": sealevel},
            facts_total_specs={"ft-global": (facts_total, wf)},
        ),
        suppress_output_types={"global"},
    )
    graph = build_execution_graph(plan)

    suppressed = sealevel.to_service_run(suppress_output_types={"global"}).args
    assert suppressed != sealevel.to_service_run().args
    assert graph.nodes["sealevel"].run.args == suppressed
    assert graph.nodes["ft-global"].run.args == facts_total.to_service_run().args
