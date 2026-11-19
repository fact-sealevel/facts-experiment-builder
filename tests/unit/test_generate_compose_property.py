"""Property tests for _build_standard_specs() and the Compose adapter's
render_compose_services()."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from hypothesis import assume, given
from hypothesis import strategies as st

from facts_experiment_builder.application import prepare_plan
from facts_experiment_builder.application.execution_graph import build_execution_graph
from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.application.prepare_plan import _build_standard_specs
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import (
    ModuleContainerImage,
    ModuleSchema,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.core.module.service_run import ServiceRun
from facts_experiment_builder.core.workflow import Workflow
from facts_experiment_builder.io.compose_backend import render_compose_services
from tests.unit.helpers import make_loaded_config


# ---------------------------------------------------------------------------
# Strategies and shared helpers
# ---------------------------------------------------------------------------

_module_name = st.from_regex(r"[a-z][a-z0-9]{2,8}", fullmatch=True)
_module_list = st.lists(_module_name, min_size=0, max_size=4, unique=True)
_nonempty_module_list = st.lists(_module_name, min_size=1, max_size=4, unique=True)

_DATA_PATHS = ExperimentDataPaths(
    shared_input_data="/in/shared",
    module_specific_input_base="/in/module",
    output_data_location="/out",
    experiment_specific_input_data=None,
)


def _minimal_schema(name: str, *, per_workflow: bool = False) -> ModuleSchema:
    return ModuleSchema(
        module_name=name,
        container_image="img:tag",
        arguments=ArgumentsSpec(),
        volumes={},
        per_workflow=per_workflow,
    )


def _fake_build_module_service_spec(
    module_section,
    *,
    config,
    module_name,
    known_module_names,
    module_definition,
    data_paths,
):
    stub = MagicMock()
    stub.module_name = module_name
    return stub


@contextmanager
def _mock_build_module_service_spec():
    """Context manager: stub build_module_service_spec for _build_standard_specs tests."""
    with patch.object(
        prepare_plan,
        "build_module_service_spec",
        _fake_build_module_service_spec,
    ):
        yield


def _stub_spec() -> MagicMock:
    """Stub ModuleServiceSpec: a minimal ServiceRun, no schema dependencies, and no
    climate file."""
    stub = MagicMock()
    stub.module_definition.uses_climate_file = False
    stub.to_service_run.return_value = ServiceRun(
        name="stub",
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        args=[],
        binds=[],
        env={},
        output_dir="/out/stub",
        host_outputs={},
    )
    stub.dependencies.return_value = []
    return stub


# ---------------------------------------------------------------------------
# _build_standard_specs — structural invariants
# ---------------------------------------------------------------------------


def _standard_specs(climate_module, sealevel_modules, schemas):
    with _mock_build_module_service_spec():
        return _build_standard_specs(
            climate_module=climate_module,
            sealevel_modules=sealevel_modules,
            config=make_loaded_config(),
            schemas=schemas,
            data_paths=_DATA_PATHS,
        )


@given(sealevel_names=_nonempty_module_list)
def test_sealevel_names_are_the_keys_without_a_climate_module(sealevel_names):
    """Without a climate module, the specs are exactly the sea-level modules."""
    schemas = {n: _minimal_schema(n) for n in sealevel_names}

    assert list(_standard_specs(None, sealevel_names, schemas)) == sealevel_names


@given(climate_name=_module_name, sealevel_names=_module_list)
def test_climate_module_comes_first_when_present(climate_name, sealevel_names):
    """The climate module's spec comes first, followed by the sea-level modules."""
    assume(climate_name not in sealevel_names)
    schemas = {n: _minimal_schema(n) for n in [climate_name, *sealevel_names]}

    assert list(_standard_specs(climate_name, sealevel_names, schemas)) == [
        climate_name,
        *sealevel_names,
    ]


# ---------------------------------------------------------------------------
# render_compose_services — structural invariants
# ---------------------------------------------------------------------------


@given(standard_names=_nonempty_module_list)
def test_standard_spec_names_appear_in_services(standard_names):
    """Every standard spec name appears as a key in the returned services dict."""
    exec_plan = _ExecutionPlan(
        standard_specs={n: _stub_spec() for n in standard_names},
        facts_total_specs={},
        esl_specs={},
        climate_service_name=standard_names[0],
        suppress_output_types=set(),
        workflow_names=[],
    )

    result = render_compose_services(build_execution_graph(exec_plan))

    assert set(standard_names) <= result.keys()


@given(ft_names=_nonempty_module_list, wf_module_names=_nonempty_module_list)
def test_facts_total_spec_names_appear_in_services(ft_names, wf_module_names):
    """Every facts-total spec name appears as a key in the returned services dict."""
    wf = Workflow(name="wf1", module_names=wf_module_names)
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={n: (_stub_spec(), wf) for n in ft_names},
        esl_specs={},
        climate_service_name=None,
        suppress_output_types=set(),
        workflow_names=[],
    )

    result = render_compose_services(build_execution_graph(exec_plan))

    assert set(ft_names) <= result.keys()


@given(esl_names=_nonempty_module_list)
def test_esl_spec_names_appear_in_services(esl_names):
    """Every ESL spec name appears as a key in the returned services dict."""
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={n: (_stub_spec(), "dep-service") for n in esl_names},
        climate_service_name=None,
        suppress_output_types=set(),
        workflow_names=[],
    )

    result = render_compose_services(build_execution_graph(exec_plan))

    assert set(esl_names) <= result.keys()


@given(
    standard_names=_module_list,
    ft_names=_module_list,
    esl_names=_module_list,
)
def test_service_count_equals_sum_of_plan_specs(standard_names, ft_names, esl_names):
    """len(services) equals the total number of specs across all plan categories."""
    all_names = standard_names + ft_names + esl_names
    assume(len(all_names) == len(set(all_names)))  # no cross-category collisions
    assume(len(all_names) > 0)

    wf = Workflow(name="wf1", module_names=["mod1"])
    exec_plan = _ExecutionPlan(
        standard_specs={n: _stub_spec() for n in standard_names},
        facts_total_specs={n: (_stub_spec(), wf) for n in ft_names},
        esl_specs={n: (_stub_spec(), "dep") for n in esl_names},
        climate_service_name=standard_names[0] if standard_names else None,
        suppress_output_types=set(),
        workflow_names=[],
    )

    result = render_compose_services(build_execution_graph(exec_plan))

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
        climate_service_name=None,
        suppress_output_types=set(),
        workflow_names=[],
    )

    result = render_compose_services(build_execution_graph(exec_plan))

    assert set(result[service_name]["depends_on"].keys()) == set(wf_module_names)


@given(service_name=_module_name, dep_service=_module_name)
def test_esl_depends_on_is_exactly_the_dep_service(service_name, dep_service):
    """Each ESL service's depends_on is exactly {dep_service_name: condition}."""
    exec_plan = _ExecutionPlan(
        standard_specs={},
        facts_total_specs={},
        esl_specs={service_name: (_stub_spec(), dep_service)},
        climate_service_name=None,
        suppress_output_types=set(),
        workflow_names=[],
    )

    result = render_compose_services(build_execution_graph(exec_plan))

    assert result[service_name]["depends_on"] == {
        dep_service: {"condition": "service_completed_successfully"}
    }
