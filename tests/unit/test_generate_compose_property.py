"""Property tests for _build_module_specs() and _build_compose_services()."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from hypothesis import assume, given
from hypothesis import strategies as st

from facts_experiment_builder.application import (
    generate_compose as generate_compose_module,
)
from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.application.generate_compose import (
    _build_compose_services,
    _build_module_specs,
)
from facts_experiment_builder.core.experiment.experiment_plan import _ExperimentPlan
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.workflow import Workflow


# ---------------------------------------------------------------------------
# Strategies and shared helpers
# ---------------------------------------------------------------------------

_module_name = st.from_regex(r"[a-z][a-z0-9]{2,8}", fullmatch=True)
_module_list = st.lists(_module_name, min_size=0, max_size=4, unique=True)
_nonempty_module_list = st.lists(_module_name, min_size=1, max_size=4, unique=True)


def _minimal_schema(name: str, *, per_workflow: bool = False) -> ModuleSchema:
    return ModuleSchema(
        module_name=name,
        container_image="img:tag",
        arguments=ArgumentsSpec(),
        volumes={},
        per_workflow=per_workflow,
    )


def _make_plan(
    *,
    climate_module_name: str = "NONE",
    sealevel_module_names: list[str] | None = None,
    framework_module_names: list[str] | None = None,
    esl_module_names: list[str] | None = None,
    workflows: dict | None = None,
) -> _ExperimentPlan:
    return _ExperimentPlan(
        experiment=MagicMock(),
        climate_module_name=climate_module_name,
        sealevel_module_names=sealevel_module_names or [],
        framework_module_names=framework_module_names or [],
        esl_module_names=esl_module_names or [],
        suppress_output_types=set(),
        workflows=workflows or {},
    )


def _fake_build_module_service_spec(
    metadata, module_name, known_module_names, module_definition
):
    stub = MagicMock()
    stub.module_name = module_name
    return stub


@contextmanager
def _mock_build_module_service_spec():
    """Context manager: stub build_module_service_spec for _build_module_specs tests."""
    with patch.object(
        generate_compose_module,
        "build_module_service_spec",
        _fake_build_module_service_spec,
    ):
        yield


@contextmanager
def _mock_execution_plan(exec_plan: _ExecutionPlan):
    """Context manager: stub build_experiment_execution_plan for _build_compose_services tests."""
    with patch.object(
        generate_compose_module,
        "build_experiment_execution_plan",
        lambda *a, **kw: exec_plan,
    ):
        yield


def _stub_spec() -> MagicMock:
    """Stub ModuleServiceSpec: generate_compose_service returns a fresh dict each call."""
    stub = MagicMock()
    stub.generate_compose_service.side_effect = lambda *a, **kw: {
        "image": "img:tag",
        "command": [],
        "volumes": [],
        "restart": "no",
    }
    return stub


def _call_build_compose_services(exec_plan: _ExecutionPlan) -> dict[str, Any]:
    with _mock_execution_plan(exec_plan):
        return _build_compose_services(
            specs=MagicMock(),
            plan=MagicMock(),
            metadata={},
            experiment_dir=Path("/fake"),
            schemas={},
        )


# ---------------------------------------------------------------------------
# _build_module_specs — structural invariants
# ---------------------------------------------------------------------------


@given(sealevel_names=_nonempty_module_list)
def test_sealevel_module_keys_match_plan(sealevel_names):
    """specs.sealevel_modules has exactly the keys from plan.sealevel_module_names."""
    plan = _make_plan(sealevel_module_names=sealevel_names)
    schemas = {n: _minimal_schema(n) for n in sealevel_names}
    schemas["NONE"] = _minimal_schema("NONE")

    with _mock_build_module_service_spec():
        result = _build_module_specs(
            plan=plan,
            metadata={},
            schemas=schemas,
            known_module_names=list(schemas.keys()),
        )

    assert set(result.sealevel_modules.keys()) == set(sealevel_names)


@given(esl_names=_nonempty_module_list)
def test_esl_module_keys_match_plan(esl_names):
    """specs.esl_modules has exactly the keys from plan.esl_module_names."""
    plan = _make_plan(esl_module_names=esl_names)
    schemas = {n: _minimal_schema(n) for n in esl_names}
    schemas["NONE"] = _minimal_schema("NONE")

    with _mock_build_module_service_spec():
        result = _build_module_specs(
            plan=plan,
            metadata={},
            schemas=schemas,
            known_module_names=list(schemas.keys()),
        )

    assert set(result.esl_modules.keys()) == set(esl_names)


@given(sealevel_names=_nonempty_module_list)
def test_climate_module_is_none_when_name_is_none(sealevel_names):
    """specs.climate_module is None for any experiment where climate_module_name is NONE."""
    plan = _make_plan(climate_module_name="NONE", sealevel_module_names=sealevel_names)
    schemas = {n: _minimal_schema(n) for n in sealevel_names}
    schemas["NONE"] = _minimal_schema("NONE")

    with _mock_build_module_service_spec():
        result = _build_module_specs(
            plan=plan,
            metadata={},
            schemas=schemas,
            known_module_names=list(schemas.keys()),
        )

    assert result.climate_module is None


@given(climate_name=_module_name)
def test_climate_module_present_when_name_is_not_none(climate_name):
    """specs.climate_module is set when plan.climate_module_name is not 'NONE'."""
    assume(climate_name.upper() != "NONE")
    plan = _make_plan(climate_module_name=climate_name)
    schemas = {climate_name: _minimal_schema(climate_name)}

    with _mock_build_module_service_spec():
        result = _build_module_specs(
            plan=plan,
            metadata={},
            schemas=schemas,
            known_module_names=list(schemas.keys()),
        )

    assert result.climate_module is not None


@given(
    framework_name=_module_name,
    sealevel_names=_nonempty_module_list,
    workflow_names=_nonempty_module_list,
)
def test_per_workflow_framework_excluded_when_workflows_present(
    framework_name, sealevel_names, workflow_names
):
    """A per_workflow=True framework module is skipped when plan.workflows is non-empty."""
    assume(framework_name not in sealevel_names)
    workflows = {n: Workflow(name=n, module_names=[]) for n in workflow_names}
    plan = _make_plan(
        sealevel_module_names=sealevel_names,
        framework_module_names=[framework_name],
        workflows=workflows,
    )
    schemas = {n: _minimal_schema(n) for n in sealevel_names}
    schemas["NONE"] = _minimal_schema("NONE")
    schemas[framework_name] = _minimal_schema(framework_name, per_workflow=True)

    with _mock_build_module_service_spec():
        result = _build_module_specs(
            plan=plan,
            metadata={},
            schemas=schemas,
            known_module_names=list(schemas.keys()),
        )

    assert framework_name not in result.framework_modules


@given(
    framework_name=_module_name,
    sealevel_names=_nonempty_module_list,
)
def test_per_workflow_framework_included_when_no_workflows(
    framework_name, sealevel_names
):
    """A per_workflow=True framework module IS included when plan.workflows is empty."""
    assume(framework_name not in sealevel_names)
    plan = _make_plan(
        sealevel_module_names=sealevel_names,
        framework_module_names=[framework_name],
        workflows={},
    )
    schemas = {n: _minimal_schema(n) for n in sealevel_names}
    schemas["NONE"] = _minimal_schema("NONE")
    schemas[framework_name] = _minimal_schema(framework_name, per_workflow=True)

    with _mock_build_module_service_spec():
        result = _build_module_specs(
            plan=plan,
            metadata={},
            schemas=schemas,
            known_module_names=list(schemas.keys()),
        )

    assert framework_name in result.framework_modules


# ---------------------------------------------------------------------------
# _build_compose_services — structural invariants
# ---------------------------------------------------------------------------


@given(standard_names=_nonempty_module_list)
def test_standard_spec_names_appear_in_services(standard_names):
    """Every standard spec name appears as a key in the returned services dict."""
    exec_plan = _ExecutionPlan(
        standard_specs={n: _stub_spec() for n in standard_names},
        facts_total_specs={},
        esl_specs={},
        standalone_esl_specs={},
        climate_service_name=standard_names[0],
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert set(standard_names) <= result.keys()


@given(ft_names=_nonempty_module_list, wf_module_names=_nonempty_module_list)
def test_facts_total_spec_names_appear_in_services(ft_names, wf_module_names):
    """Every facts-total spec name appears as a key in the returned services dict."""
    wf = Workflow(name="wf1", module_names=wf_module_names)
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={n: (_stub_spec(), wf) for n in ft_names},
        esl_specs={},
        standalone_esl_specs={},
        climate_service_name=None,
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert set(ft_names) <= result.keys()


@given(esl_names=_nonempty_module_list)
def test_esl_spec_names_appear_in_services(esl_names):
    """Every ESL spec name appears as a key in the returned services dict."""
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={n: (_stub_spec(), "dep-service") for n in esl_names},
        standalone_esl_specs={},
        climate_service_name=None,
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert set(esl_names) <= result.keys()


@given(standalone_names=_nonempty_module_list)
def test_standalone_esl_spec_names_appear_in_services(standalone_names):
    """Every standalone ESL spec name appears as a key in the returned services dict."""
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={},
        standalone_esl_specs={n: _stub_spec() for n in standalone_names},
        climate_service_name=None,
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert set(standalone_names) <= result.keys()


@given(
    standard_names=_module_list,
    ft_names=_module_list,
    esl_names=_module_list,
    standalone_names=_module_list,
)
def test_service_count_equals_sum_of_plan_specs(
    standard_names, ft_names, esl_names, standalone_names
):
    """len(services) equals the total number of specs across all plan categories."""
    all_names = standard_names + ft_names + esl_names + standalone_names
    assume(len(all_names) == len(set(all_names)))  # no cross-category collisions
    assume(len(all_names) > 0)

    wf = Workflow(name="wf1", module_names=["mod1"])
    exec_plan = _ExecutionPlan(
        standard_specs={n: _stub_spec() for n in standard_names},
        facts_total_specs={n: (_stub_spec(), wf) for n in ft_names},
        esl_specs={n: (_stub_spec(), "dep") for n in esl_names},
        standalone_esl_specs={n: _stub_spec() for n in standalone_names},
        climate_service_name=standard_names[0] if standard_names else None,
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert len(result) == len(all_names)


@given(service_name=_module_name, wf_module_names=_nonempty_module_list)
def test_facts_total_depends_on_matches_workflow_module_names(
    service_name, wf_module_names
):
    """Each facts-total service's depends_on keys equal the workflow's module_names."""
    wf = Workflow(name="wf1", module_names=wf_module_names)
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={service_name: (_stub_spec(), wf)},
        esl_specs={},
        standalone_esl_specs={},
        climate_service_name=None,
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert set(result[service_name]["depends_on"].keys()) == set(wf_module_names)


@given(service_name=_module_name, dep_service=_module_name)
def test_esl_depends_on_is_exactly_the_dep_service(service_name, dep_service):
    """Each ESL service's depends_on is exactly {dep_service_name: condition}."""
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={service_name: (_stub_spec(), dep_service)},
        standalone_esl_specs={},
        climate_service_name=None,
        suppress_output_types=set(),
    )

    result = _call_build_compose_services(exec_plan)

    assert result[service_name]["depends_on"] == {
        dep_service: {"condition": "service_completed_successfully"}
    }
