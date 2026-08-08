from hypothesis import given, strategies as st, event
import string
import os
from pathlib import Path

from facts_experiment_builder.io.paths import ExperimentPaths
from facts_experiment_builder.core.experiment.name import (
    ExperimentName,
    InvalidExperimentNameError,
    _VALID,
)

# Make strategies that produce possible experiment names and
# includes experiment names that have parent directories

name = st.text(alphabet=st.sampled_from("abZ019._-/n\~"), min_size=1)
path_st = st.builds(
    lambda parts, trailing: "/".join(parts) + (trailing or ""),
    parts=st.lists(name, min_size=1, max_size=3),
    trailing=st.sampled_from(["", "/"]),
)

# strategy for raw names
raw_names = st.one_of(
    st.text(),
    st.sampled_from(
        [
            ".",
            "..",
            "...",
            "a/..",
            "./foo",
            "a/./b",
            "foo.",
            ".hidden",
            "CON",
            "a\n/b",
            "",
            " ",
            "a" * 300,
        ]
    ),
)

# strategy for valid experiment names
_ALPHABET = string.ascii_letters + string.digits + "._-"
_FIRST = string.ascii_letters + string.digits

segment = st.builds(
    lambda first, second: first + second,
    st.sampled_from(_FIRST),
    st.text(alphabet=_ALPHABET, max_size=7),
)

valid_names = st.builds(
    ExperimentName,
    parent=st.one_of(
        st.none(),
        st.lists(segment, min_size=1, max_size=2).map(lambda ps: Path("/".join(ps))),
    ),
    name=segment,
)


@given(raw_names)
def test_parse_raises_only_its_own_error(raw):
    try:
        ExperimentName.parse(raw)
    except InvalidExperimentNameError:
        event("rejected")
    else:
        event("accepted")


@given(valid_names)
def test_experiment_dir_never_escapes_workspace(name):
    ws = Path("/ws")
    try:
        d = Path(
            os.path.normpath(
                ExperimentPaths(workspace_dir=ws, experiment_name=name).experiment_dir
            )
        )
    except InvalidExperimentNameError:
        return

    assert d.is_relative_to(ws) and d != ws


@given(valid_names)
def test_roundtrip(name):
    try:
        name = ExperimentName.parse(str(name))

    except InvalidExperimentNameError:
        return

    assert ExperimentName.parse(str(name)) == name


@given(name=valid_names)
def test_accepted_names_are_writable(name, tmp_path_factory):
    ws = tmp_path_factory.mktemp("ws")
    ExperimentPaths(workspace_dir=ws, experiment_name=name).experiment_dir.mkdir(
        parents=True, exist_ok=True
    )


@given(path_st)
def test_parse_either_rejects_or_yields_a_wellformed_name(raw):
    try:
        name = ExperimentName.parse(raw)
    except InvalidExperimentNameError:
        return
    p = name.relative_path
    assert p.parts and not p.is_absolute() and ".." not in p.parts
    assert all(_VALID.fullmatch(s) for s in p.parts)


@given(path_st)
def test_relative_path_returns_relpath_if_parent_present(raw):
    try:
        name = ExperimentName.parse(raw)
    except InvalidExperimentNameError:
        return
    if "/" not in raw:
        assert "/" not in name.relative_path.as_posix()
