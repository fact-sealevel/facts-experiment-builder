from hypothesis import given, strategies as st
from facts_experiment_builder.core.workflow import (
    Workflow,
    WorkflowName,
    _VALID_WORKFLOW_NAME,
    workflows_from_metadata,
)
import pytest

valid_names = st.from_regex(_VALID_WORKFLOW_NAME, fullmatch=True)
clean_module_name = st.from_regex(r"\A[A-Za-z0-9_-]+\Z", fullmatch=True)
valid_module_list_value = st.one_of(
    st.lists(clean_module_name, unique=True, max_size=4).map(",".join),
    st.lists(clean_module_name, unique=True, max_size=4),
)


@given(valid_names)
def test_valid_names_always_accepted(name):
    """Valid names should always be accepted by WorkflowName."""
    workflow_name = WorkflowName(name=name)
    assert workflow_name.name == name


@given(st.text(min_size=1).filter(lambda s: not _VALID_WORKFLOW_NAME.match(s)))
def test_invalid_names_always_rejected(name):
    with pytest.raises(ValueError):
        WorkflowName(name=name)


def test_empty_name_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        WorkflowName(name="")


def test_non_string_name_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        WorkflowName(name=123)


@given(valid_names, st.integers(min_value=0))
def test_embedded_comma_always_rejected(name, pos):
    i = pos % (len(name) + 1)
    tainted = name[:i] + "," + name[i:]
    with pytest.raises(ValueError):
        WorkflowName(name=tainted)


@given(valid_names, st.integers(min_value=0))
def test_embedded_space_always_rejected(name, pos):
    i = pos % (len(name) + 1)
    tainted = name[:i] + " " + name[i:]
    with pytest.raises(ValueError):
        WorkflowName(name=tainted)


@given(valid_names, st.integers(min_value=0))
def test_embedded_period_accepted(name, pos):
    i = pos % (len(name) + 1)
    tainted = name[:i] + "." + name[i:]
    workflow_name = WorkflowName(name=tainted)
    assert workflow_name.name == tainted


# --- Workflow.from_module_list_str ---


def test_from_module_list_str_creates_workflow_with_correct_name():
    wf = Workflow.from_module_list_str("wf1", "tlm-sterodynamics")
    assert isinstance(wf, Workflow)
    assert wf.name == "wf1"


def test_from_module_list_str_parses_comma_separated_modules():
    wf = Workflow.from_module_list_str(
        "wf1", "fittedismip-gris,tlm-sterodynamics,ssp-landwaterstorage"
    )
    assert wf.module_names == [
        "fittedismip-gris",
        "tlm-sterodynamics",
        "ssp-landwaterstorage",
    ]


def test_from_module_list_str_strips_whitespace_around_modules():
    wf = Workflow.from_module_list_str("wf1", "  fittedismip-gris , tlm-sterodynamics ")
    assert wf.module_names == ["fittedismip-gris", "tlm-sterodynamics"]


def test_from_module_list_str_filters_empty_entries():
    """Double commas and a trailing comma should not produce empty-string entries."""
    wf = Workflow.from_module_list_str("wf1", "fittedismip-gris,,tlm-sterodynamics,")
    assert wf.module_names == ["fittedismip-gris", "tlm-sterodynamics"]


def test_from_module_list_str_single_module_no_comma():
    wf = Workflow.from_module_list_str("wf1", "tlm-sterodynamics")
    assert wf.module_names == ["tlm-sterodynamics"]


@pytest.mark.parametrize("module_list_str", ["", None])
def test_from_module_list_str_empty_or_none_gives_empty_list(module_list_str):
    wf = Workflow.from_module_list_str("wf1", module_list_str)
    assert wf.module_names == []


@given(
    st.lists(
        st.from_regex(r"\A[A-Za-z0-9_-]+\Z", fullmatch=True),
        min_size=1,
        max_size=6,
        unique=True,
    )
)
def test_from_module_list_str_round_trips_through_to_module_list_str(modules):
    """Joining a clean module list and re-parsing it reproduces the same list."""
    wf = Workflow.from_module_list_str("wf1", ",".join(modules))
    assert wf.module_names == modules


# --- Workflow.__post_init__ (module_names validation) ---


def test_workflow_accepts_valid_module_names():
    wf = Workflow(name="wf1", module_names=["fittedismip-gris", "tlm-sterodynamics"])
    assert wf.module_names == ["fittedismip-gris", "tlm-sterodynamics"]


def test_workflow_accepts_empty_module_names():
    wf = Workflow(name="wf1", module_names=[])
    assert wf.module_names == []


def test_workflow_rejects_non_list_module_names():
    with pytest.raises(ValueError, match="must be a list"):
        Workflow(name="wf1", module_names="fittedismip-gris")


@pytest.mark.parametrize("bad_module_names", [[""], ["   "], [123], [None]])
def test_workflow_rejects_non_empty_string_entries(bad_module_names):
    with pytest.raises(ValueError, match="non-empty strings"):
        Workflow(name="wf1", module_names=bad_module_names)


def test_workflow_rejects_duplicate_module_names():
    with pytest.raises(ValueError, match="duplicates"):
        Workflow(name="wf1", module_names=["fittedismip-gris", "fittedismip-gris"])


def test_to_module_list_str_returns_comma_separated_string():
    wf = Workflow(name="wf1", module_names=["fittedismip-gris", "tlm-sterodynamics"])
    assert wf.to_module_list_str() == "fittedismip-gris,tlm-sterodynamics"


def test_from_dict_returns_workflow_for_string_value():
    wf = Workflow.from_dict("wf1", "fittedismip-gris,tlm-sterodynamics")
    assert wf.name == "wf1"
    assert wf.module_names == ["fittedismip-gris", "tlm-sterodynamics"]


def test_from_dict_accepts_list_value():
    wf = Workflow.from_dict("wf1", ["fittedismip-gris", "tlm-sterodynamics"])
    assert wf.name == "wf1"
    assert wf.module_names == ["fittedismip-gris", "tlm-sterodynamics"]


def test_to_dict_calls_to_module_list_str_if_receives_list_value():
    wf = Workflow(name="wf1", module_names=["fittedismip-gris", "tlm-sterodynamics"])
    dict_value = wf.to_dict_value()
    assert dict_value == "fittedismip-gris,tlm-sterodynamics"


def test_total_output_filename_includes_wf_name():
    wf = Workflow(name="wf1", module_names=["fittedismip-gris"])
    assert wf.total_output_filename == "wf1_total.nc"


# --- workflows_from_metadata ---


@given(st.one_of(st.none(), st.text(), st.lists(st.text()), st.integers()))
def test_workflows_from_metadata_non_dict_workflows_gives_empty_dict(bad_workflows):
    """When metadata['workflows'] is missing or not a dict, returns {}."""
    assert workflows_from_metadata({"workflows": bad_workflows}) == {}


@given(st.dictionaries(valid_names, valid_module_list_value, max_size=5))
def test_workflows_from_metadata_all_valid_entries_round_trip(raw):
    """Every valid (name, value) pair survives and matches Workflow.from_dict
    directly."""
    result = workflows_from_metadata({"workflows": raw})
    assert result.keys() == raw.keys()
    for name, value in raw.items():
        assert result[name] == Workflow.from_dict(name, value)


@given(
    st.dictionaries(valid_names, valid_module_list_value, max_size=3),
    st.dictionaries(
        st.one_of(st.just(""), st.integers(), st.none()),
        valid_module_list_value,
        max_size=3,
    ),
)
def test_workflows_from_metadata_invalid_keys_are_skipped(
    valid_entries, invalid_key_entries
):
    """Falsy or non-string keys are dropped; valid string keys are kept."""
    raw = {**valid_entries, **invalid_key_entries}
    result = workflows_from_metadata({"workflows": raw})
    assert result.keys() == valid_entries.keys()


@given(st.dictionaries(valid_names, valid_module_list_value, min_size=1, max_size=3))
def test_workflows_from_metadata_any_invalid_value_raises_and_discards_whole_batch(
    valid_entries,
):
    """One entry with an invalid value (e.g. duplicate module names) raises,
    even with otherwise-valid entries present -- this is the current, intentional
    fail-fast behavior (no partial results are returned)."""
    bad_name = "this-one-is-bad"
    raw = {**valid_entries, bad_name: "dup,dup"}
    with pytest.raises(ValueError):
        workflows_from_metadata({"workflows": raw})
