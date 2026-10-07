"""Characterization tests for module-level host path resolution.

These pin the observable behavior of resolving experiment-level path keys
(shared-input-data, module-specific-input-data, output-data-location,
experiment-specific-input-data) into per-module ResolvedPaths, so the refactor
that resolves experiment-level paths once per experiment can be checked for
behavior changes. Only `_resolve()` should need to change across the refactor.
"""

import os
from typing import Any

import pytest

from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_path_resolution import (
    resolve_experiment_data_paths,
    resolve_module_paths,
)


def _schema(module_name: str, input_dir_name: str | None = None) -> ModuleSchema:
    extra = {"input_dir_name": input_dir_name} if input_dir_name else {}
    return ModuleSchema(
        module_name=module_name,
        container_image="img:tag",
        arguments=ArgumentsSpec(),
        volumes={},
        extra=extra,
    )


def _metadata(
    module_name: str, section: dict | None = None, /, **paths: Any
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "shared-input-data": "/in/shared",
        "module-specific-input-data": "/in/module",
        "output-data-location": "/out",
    }
    metadata.update(paths)
    metadata[module_name] = section if section is not None else {}
    return metadata


def _resolve(
    metadata: dict,
    module_name: str,
    schema: ModuleSchema,
    known_module_names: list[str] | None = None,
):
    return resolve_module_paths(
        data_paths=resolve_experiment_data_paths(metadata),
        module_metadata=metadata[module_name],
        module_name=module_name,
        module_definition=schema,
        known_module_names=known_module_names or [],
    )


# ---------------------------------------------------------------------------
# Per-module path construction
# ---------------------------------------------------------------------------


def test_standard_module_paths():
    resolved = _resolve(
        _metadata("fair-temperature"), "fair-temperature", _schema("fair-temperature")
    )
    assert resolved.shared_input_data == "/in/shared"
    assert resolved.module_specific_input_data == "/in/module/fair-temperature"
    assert resolved.output_data_location == "/out/fair-temperature"
    assert resolved.experiment_specific_input_data is None
    assert resolved.output_container_base is None


def test_input_dir_name_overrides_module_name_for_input_dir_only():
    resolved = _resolve(
        _metadata("ipccar5-glaciers"),
        "ipccar5-glaciers",
        _schema("ipccar5-glaciers", input_dir_name="ipccar5"),
    )
    assert resolved.module_specific_input_data == "/in/module/ipccar5"
    assert resolved.output_data_location == "/out/ipccar5-glaciers"


def test_per_workflow_service_uses_schema_name_for_input_and_service_name_for_output():
    service = "extremesealevel-pointsoverthreshold-wf1"
    resolved = _resolve(
        _metadata(service), service, _schema("extremesealevel-pointsoverthreshold")
    )
    assert (
        resolved.module_specific_input_data
        == "/in/module/extremesealevel-pointsoverthreshold"
    )
    assert resolved.output_data_location == f"/out/{service}"
    assert resolved.output_container_base is None


def test_facts_total_service_shares_output_dir_and_default_container_base():
    service = "facts-total-wf1-global"
    resolved = _resolve(_metadata(service), service, _schema("facts-total"))
    assert resolved.output_data_location == "/out/facts-total"
    assert resolved.output_container_base == "/mnt/total_out/facts-total"


def test_facts_total_container_base_from_module_section():
    service = "facts-total-wf1-local"
    resolved = _resolve(
        _metadata(service, {"_output_container_base": "/mnt/custom"}),
        service,
        _schema("facts-total"),
    )
    assert resolved.output_data_location == "/out/facts-total"
    assert resolved.output_container_base == "/mnt/custom"


def test_module_specific_base_ending_in_known_module_is_replaced_by_parent():
    resolved = _resolve(
        _metadata(
            "tlm-sterodynamics",
            **{"module-specific-input-data": "/in/module/fair-temperature"},
        ),
        "tlm-sterodynamics",
        _schema("tlm-sterodynamics"),
        known_module_names=["fair-temperature", "tlm-sterodynamics"],
    )
    assert resolved.module_specific_input_data == "/in/module/tlm-sterodynamics"


def test_module_specific_base_ending_in_unknown_name_is_kept():
    resolved = _resolve(
        _metadata(
            "tlm-sterodynamics", **{"module-specific-input-data": "/in/module/other"}
        ),
        "tlm-sterodynamics",
        _schema("tlm-sterodynamics"),
        known_module_names=["fair-temperature", "tlm-sterodynamics"],
    )
    assert resolved.module_specific_input_data == "/in/module/other/tlm-sterodynamics"


# ---------------------------------------------------------------------------
# experiment-specific-input-data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("/exp/data", "/exp/data"),
        ({"value": "/exp/data"}, "/exp/data"),
        (["/exp/data", "/exp/other"], "/exp/data"),
        ([], None),
        ("", None),
        (None, None),
    ],
)
def test_experiment_specific_input_data(value, expected):
    resolved = _resolve(
        _metadata("m", **{"experiment-specific-input-data": value}), "m", _schema("m")
    )
    assert resolved.experiment_specific_input_data == expected


def test_experiment_specific_input_data_missing_is_none():
    resolved = _resolve(_metadata("m"), "m", _schema("m"))
    assert resolved.experiment_specific_input_data is None


# ---------------------------------------------------------------------------
# Expansion (~, env vars, relative paths)
# ---------------------------------------------------------------------------


def test_tilde_is_expanded():
    resolved = _resolve(
        _metadata("m", **{"output-data-location": "~/out"}), "m", _schema("m")
    )
    assert resolved.output_data_location == os.path.expanduser("~") + "/out/m"


def test_env_var_is_expanded(monkeypatch):
    monkeypatch.setenv("FEB_TEST_SHARED", "/env/shared")
    resolved = _resolve(
        _metadata("m", **{"shared-input-data": "$FEB_TEST_SHARED/x"}), "m", _schema("m")
    )
    assert resolved.shared_input_data == "/env/shared/x"


def test_relative_paths_resolve_against_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cwd = os.getcwd()
    resolved = _resolve(
        _metadata(
            "m",
            **{
                "shared-input-data": "./data/shared",
                "module-specific-input-data": "./data/module",
                "output-data-location": "./out",
            },
        ),
        "m",
        _schema("m"),
    )
    assert resolved.shared_input_data == f"{cwd}/data/shared"
    assert resolved.module_specific_input_data == f"{cwd}/data/module/m"
    assert resolved.output_data_location == f"{cwd}/out/m"


# ---------------------------------------------------------------------------
# Only the template's key names are accepted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "primary, alternative",
    [
        ("shared-input-data", "shared_input_data"),
        ("module-specific-input-data", "module_specific_input_data"),
        ("output-data-location", "output_data_location"),
        ("output-data-location", "output-path"),
        ("output-data-location", "output_path"),
    ],
)
def test_alternative_key_spelling_counts_as_missing(primary, alternative):
    """Formerly accepted alternative spellings are no longer read."""
    metadata = _metadata("m")
    del metadata[primary]
    metadata[alternative] = "/alt"
    with pytest.raises(KeyError, match=primary):
        _resolve(metadata, "m", _schema("m"))


def test_alternative_key_spelling_is_ignored_when_primary_present():
    metadata = _metadata("m", output_path="/alt")
    resolved = _resolve(metadata, "m", _schema("m"))
    assert resolved.output_data_location == "/out/m"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key", ["shared-input-data", "module-specific-input-data", "output-data-location"]
)
def test_missing_required_key_raises_key_error(key):
    metadata = _metadata("m")
    del metadata[key]
    with pytest.raises(KeyError, match=key):
        _resolve(metadata, "m", _schema("m"))


@pytest.mark.parametrize(
    "key", ["shared-input-data", "module-specific-input-data", "output-data-location"]
)
def test_none_required_key_raises_value_error(key):
    with pytest.raises(ValueError, match=key):
        _resolve(_metadata("m", **{key: None}), "m", _schema("m"))


@pytest.mark.parametrize(
    "key", ["shared-input-data", "module-specific-input-data", "output-data-location"]
)
def test_value_dict_for_required_key_raises_value_error(key):
    """{"value": ...} is not unwrapped for the three required keys (only for the
    optional experiment-specific-input-data)."""
    with pytest.raises(ValueError, match=key):
        _resolve(_metadata("m", **{key: {"value": "/x"}}), "m", _schema("m"))
