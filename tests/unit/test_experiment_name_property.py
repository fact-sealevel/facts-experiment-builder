"""Property tests for ExperimentName parsing and validation."""

import string
from pathlib import Path

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from facts_experiment_builder.core.experiment.name import (
    ExperimentName,
    InvalidExperimentNameError,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_ALLOWED = string.ascii_letters + string.digits + "._-"

# A single valid path component: allowed characters only, never "." or "..".
_part = st.text(alphabet=_ALLOWED, min_size=1, max_size=12).filter(
    lambda s: s not in (".", "..")
)
_parts = st.lists(_part, min_size=1, max_size=4)

# Any character outside the allowed set, excluding the path separator (which
# would split the component) and surrogates (not valid in str paths).
_bad_char = st.characters(
    blacklist_characters=_ALLOWED + "/", blacklist_categories=("Cs",)
)


def _reason(exc_info: pytest.ExceptionInfo[InvalidExperimentNameError]) -> str:
    """The error's reason, which must be set for every validation failure."""
    reason = exc_info.value.reason
    assert reason is not None
    return reason


def _expected_parent(parts: list[str]) -> Path | None:
    return Path(*parts[:-1]) if len(parts) > 1 else None


# ---------------------------------------------------------------------------
# Valid names
# ---------------------------------------------------------------------------


@given(parts=_parts)
def test_parse_valid_name_splits_into_parent_and_name(parts):
    """A name built from valid components parses into its parent and last component."""
    raw = "/".join(parts)
    result = ExperimentName.parse(raw)
    assert result.name == parts[-1]
    assert result.parent == _expected_parent(parts)


@given(parts=_parts)
def test_parse_roundtrips_through_str_and_relative_path(parts):
    """str() and relative_path reproduce the parsed name."""
    raw = "/".join(parts)
    result = ExperimentName.parse(raw)
    assert str(result) == raw
    assert result.relative_path == Path(raw)
    assert ExperimentName.parse(str(result)) == result


@given(
    parts=_parts,
    lead=st.text(alphabet=" \t\n", max_size=3),
    trail=st.text(alphabet=" \t\n", max_size=3),
)
def test_parse_ignores_surrounding_whitespace(parts, lead, trail):
    """Leading/trailing whitespace on the whole input is stripped."""
    raw = "/".join(parts)
    assert ExperimentName.parse(lead + raw + trail) == ExperimentName.parse(raw)


@given(parts=_parts)
def test_direct_construction_matches_parse(parts):
    """Constructing directly from valid components equals parsing the joined name."""
    direct = ExperimentName(_expected_parent(parts), parts[-1])
    assert direct == ExperimentName.parse("/".join(parts))


# ---------------------------------------------------------------------------
# Invalid names
# ---------------------------------------------------------------------------


@given(
    parts=_parts,
    index=st.integers(min_value=0),
    prefix=_part,
    bad=_bad_char,
    suffix=_part,
)
def test_parse_rejects_disallowed_character_in_any_component(
    parts, index, prefix, bad, suffix
):
    """A disallowed character inside any component is rejected; the error reports the
    raw input, and its reason names the offending component and character."""
    parts = list(parts)
    bad_part = prefix + bad + suffix
    parts[index % len(parts)] = bad_part
    raw = "/".join(parts)
    with pytest.raises(InvalidExperimentNameError) as exc_info:
        ExperimentName.parse(raw)
    assert exc_info.value.raw_name == raw
    assert repr(bad_part) in _reason(exc_info)
    assert repr(bad) in _reason(exc_info)


@given(parent_parts=_parts, name=_part, bad=st.sampled_from(["\n", " ", "\t", "$"]))
@example(parent_parts=["a"], name="b", bad="\n")
def test_parse_rejects_disallowed_character_at_end_of_parent_component(
    parent_parts, name, bad
):
    """A disallowed character at the end of a parent component is rejected.

    Regression: re.match with a `$` anchor accepted a trailing newline, so
    'a\\n/b' used to parse with parent 'a\\n'.
    """
    parent_parts = list(parent_parts)
    parent_parts[-1] = parent_parts[-1] + bad
    with pytest.raises(InvalidExperimentNameError) as exc_info:
        ExperimentName.parse("/".join([*parent_parts, name]))
    assert repr(parent_parts[-1]) in _reason(exc_info)
    assert repr(bad) in _reason(exc_info)


@given(before=st.lists(_part, max_size=3), after=st.lists(_part, max_size=3))
def test_parse_rejects_dotdot_component_anywhere(before, after):
    """A '..' component is rejected wherever it appears."""
    with pytest.raises(InvalidExperimentNameError) as exc_info:
        ExperimentName.parse("/".join([*before, "..", *after]))
    assert "'..' is not allowed" in _reason(exc_info)


@given(parts=_parts)
def test_parse_rejects_absolute_paths(parts):
    with pytest.raises(InvalidExperimentNameError) as exc_info:
        ExperimentName.parse("/" + "/".join(parts))
    assert _reason(exc_info) == "Parent directory must be a relative path."


@pytest.mark.parametrize("raw", ["", ".", "..", "/"])
def test_parse_rejects_empty_and_dot_only_names(raw):
    with pytest.raises(InvalidExperimentNameError) as exc_info:
        ExperimentName.parse(raw)
    assert _reason(exc_info)


@given(
    parts=_parts,
    index=st.integers(min_value=0),
    bad_part=st.just("..")
    | st.builds(lambda p, b, s: p + b + s, _part, _bad_char, _part),
)
def test_parse_keeps_the_reason_from_validation(parts, index, bad_part):
    """parse() reports the same reason as constructing from the same components,
    rather than replacing it with a generic message.

    '.' and '' components are excluded: pathlib drops them when parsing, so parse()
    and direct construction legitimately differ for them.
    """
    parts = list(parts)
    parts[index % len(parts)] = bad_part
    parent = Path(*parts[:-1]) if len(parts) > 1 else None
    with pytest.raises(InvalidExperimentNameError) as direct:
        ExperimentName(parent, parts[-1])
    with pytest.raises(InvalidExperimentNameError) as parsed:
        ExperimentName.parse("/".join(parts))
    assert parsed.value.reason == direct.value.reason


def test_error_message_includes_raw_name_and_reason():
    with pytest.raises(InvalidExperimentNameError) as exc_info:
        ExperimentName.parse("funky experiments/my_exp")
    message = str(exc_info.value)
    assert "'funky experiments/my_exp'" in message
    assert _reason(exc_info) in message
    assert "' '" in _reason(exc_info)


@given(name=st.sampled_from(["", ".", ".."]) | st.builds(lambda b: "x" + b, _bad_char))
def test_direct_construction_rejects_invalid_name(name):
    with pytest.raises(InvalidExperimentNameError):
        ExperimentName(None, name)


@given(
    parts=_parts,
    bad_parent=st.sampled_from([Path("/abs"), Path("."), Path("a/.."), Path("a b")]),
)
def test_direct_construction_rejects_invalid_parent(parts, bad_parent):
    with pytest.raises(InvalidExperimentNameError):
        ExperimentName(bad_parent, parts[-1])
