"""Tests for io/write_compose.py: make_compose_yaml and write_compose_yaml.

format_compose_yaml is intentionally not tested here -- it is dead code (never
called by the generate-compose CLI or anywhere else in the codebase).
"""

import yaml
from hypothesis import HealthCheck, given, settings, strategies as st

from facts_experiment_builder.io.write_compose import (
    make_compose_yaml,
    write_compose_yaml,
)

# --- make_compose_yaml: example-based round-trip ---


def test_make_compose_yaml_round_trips_a_representative_compose_dict():
    """A dict shaped like generate_compose.py's real output (nested depends_on,
    list-valued command/volumes) survives make_compose_yaml -> yaml.safe_load
    unchanged."""
    content_dict = {
        "services": {
            "fair-temperature": {
                "image": "ghcr.io/fact-sealevel/fair-temperature:0.2.1",
                "command": [
                    "--pipeline-id",
                    "my-experiment-ssp585",
                    "--nsamps",
                    "2000",
                ],
                "volumes": [
                    "/data/module_specific_input_data/fair-temperature:/mnt/module_specific_in"
                ],
                "restart": "no",
            },
            "fittedismip-gris": {
                "image": "ghcr.io/fact-sealevel/fittedismip-gris:0.1.2",
                "depends_on": {
                    "fair-temperature": {"condition": "service_completed_successfully"}
                },
            },
        }
    }
    yaml_content = make_compose_yaml(content_dict=content_dict)
    assert yaml.safe_load(yaml_content) == content_dict


def test_make_compose_yaml_round_trips_empty_dict():
    assert yaml.safe_load(make_compose_yaml(content_dict={})) == {}


def test_make_compose_yaml_preserves_insertion_order():
    """sort_keys=False means service order in the dict is preserved in the output."""
    content_dict = {"services": {"zzz-module": {}, "aaa-module": {}}}
    yaml_content = make_compose_yaml(content_dict=content_dict)
    assert yaml_content.index("zzz-module") < yaml_content.index("aaa-module")


def test_make_compose_yaml_does_not_wrap_long_lines():
    """width=1000 should prevent yaml.dump from line-wrapping a long value."""
    long_value = "x" * 500
    content_dict = {"services": {"mod": {"image": long_value}}}
    yaml_content = make_compose_yaml(content_dict=content_dict)
    assert long_value in yaml_content
    assert yaml.safe_load(yaml_content) == content_dict


def test_make_compose_yaml_preserves_unicode():
    content_dict = {"services": {"mod": {"label": "café ☃"}}}
    yaml_content = make_compose_yaml(content_dict=content_dict)
    assert "café" in yaml_content
    assert yaml.safe_load(yaml_content) == content_dict


# --- make_compose_yaml: property-based round-trip ---

_service_name = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), max_codepoint=0x24F),
    min_size=1,
    max_size=15,
)
# Excludes control/surrogate/line-separator characters (e.g. U+0085 NEL), which
# PyYAML does not round-trip losslessly and which never occur in real compose
# content (image names, paths, CLI args).
_printable_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs", "Zl", "Zp")),
    max_size=60,
)
_scalar_value = st.one_of(
    _printable_text,
    st.integers(),
    st.booleans(),
)
_list_value = st.lists(_printable_text.filter(bool), max_size=5)
_depends_on_value = st.dictionaries(
    _service_name,
    st.fixed_dictionaries(
        {"condition": st.sampled_from(["service_completed_successfully"])}
    ),
    max_size=3,
)
_service_dict = st.fixed_dictionaries(
    {},
    optional={
        "image": _printable_text.filter(bool),
        "command": _list_value,
        "volumes": _list_value,
        "restart": st.sampled_from(["no", "on-failure", "always"]),
        "depends_on": _depends_on_value,
    },
)
compose_dicts = st.dictionaries(_service_name, _service_dict, max_size=4).map(
    lambda services: {"services": services}
)


@given(compose_dicts)
def test_make_compose_yaml_round_trips_arbitrary_compose_shaped_dicts(content_dict):
    yaml_content = make_compose_yaml(content_dict=content_dict)
    assert yaml.safe_load(yaml_content) == content_dict


# --- write_compose_yaml ---


def test_write_compose_yaml_writes_content_to_file(tmp_path):
    path = tmp_path / "docker-compose.yaml"
    content = "services:\n   fair-temperature:\n      image: img:tag\n"

    write_compose_yaml(compose_content=content, compose_path=path)

    assert path.read_text() == content


def test_write_compose_yaml_overwrites_existing_file(tmp_path):
    path = tmp_path / "docker-compose.yaml"
    path.write_text("stale content from a previous run")

    write_compose_yaml(compose_content="fresh content", compose_path=path)

    assert path.read_text() == "fresh content"


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(compose_dicts)
def test_write_compose_yaml_then_reload_matches_original_dict(tmp_path, content_dict):
    """End-to-end: make_compose_yaml + write_compose_yaml + yaml.safe_load reproduces
    the original dict.

    Suppresses the function-scoped-fixture health check: tmp_path is reused across
    generated examples, but each example writes then immediately re-reads its own
    file, so there is no cross-example state dependency.
    """
    path = tmp_path / "docker-compose.yaml"
    yaml_content = make_compose_yaml(content_dict=content_dict)

    write_compose_yaml(compose_content=yaml_content, compose_path=path)

    assert yaml.safe_load(path.read_text()) == content_dict
