import pytest
from facts_experiment_builder.core.module.module_experiment_spec import (
    _resolve_filename,
    _options_defaults_from_schema,
    _build_options_context,
    _build_outputs,
    _build_section_from_fields,
    ModuleExperimentSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema


# ---------------------------------------------------------------------------
# _resolve_filename — single-key format (existing behaviour)
# ---------------------------------------------------------------------------


def test_resolve_filename_single_key_hit():
    arg_spec = {"filename_map": {"region": {"ALL": "output-ALL.nc"}}}
    assert _resolve_filename(arg_spec, {"region": "ALL"}) == "output-ALL.nc"


def test_resolve_filename_single_key_miss_returns_fallback():
    arg_spec = {
        "filename_map": {"region": {"ALL": "output-ALL.nc"}},
        "filename": "default.nc",
    }
    assert _resolve_filename(arg_spec, {"region": "UNKNOWN"}) == "default.nc"


def test_resolve_filename_single_key_list_value_does_not_raise():
    """List values in options_context must not cause TypeError in single-key branch."""
    arg_spec = {
        "filename_map": {"region": {"ALL": "output-ALL.nc"}},
        "filename": "default.nc",
    }
    # region is a list — single-key format skips it and returns the fallback filename
    result = _resolve_filename(arg_spec, {"region": ["ALL", "WAIS"]})
    assert result == "default.nc"


def test_resolve_filename_no_map_returns_filename():
    arg_spec = {"filename": "fallback.nc"}
    assert _resolve_filename(arg_spec, {}) == "fallback.nc"


# ---------------------------------------------------------------------------
# _resolve_filename — multi-key format
# ---------------------------------------------------------------------------

MULTI_KEY_SPEC = {
    "name": "emu-file",
    "filename_map": {
        "keys": ["pyear_end", "region"],
        "map": {
            2300: {
                "ALL": "AIS_ALL_2300.RData",
                "WAIS": "AIS_WAIS_2300.RData",
            },
            2100: {
                "ALL": "AIS_ALL_2100.RData",
            },
        },
    },
}


def test_resolve_filename_multi_key_scalar_hit():
    ctx = {"pyear_end": 2300, "region": "ALL"}
    assert _resolve_filename(MULTI_KEY_SPEC, ctx) == "AIS_ALL_2300.RData"


def test_resolve_filename_multi_key_int_key_tolerance():
    """YAML parses integer keys as int; string lookup via str() must succeed."""
    ctx = {"pyear_end": "2300", "region": "ALL"}  # pyear_end provided as string
    assert _resolve_filename(MULTI_KEY_SPEC, ctx) == "AIS_ALL_2300.RData"


def test_resolve_filename_multi_key_list_region_returns_list():
    ctx = {"pyear_end": 2300, "region": ["ALL", "WAIS"]}
    result = _resolve_filename(MULTI_KEY_SPEC, ctx)
    assert result == ["AIS_ALL_2300.RData", "AIS_WAIS_2300.RData"]


def test_resolve_filename_multi_key_miss_with_fallback_returns_fallback():
    spec = dict(MULTI_KEY_SPEC)
    spec["filename"] = "default.RData"
    ctx = {"pyear_end": 2400, "region": "ALL"}  # 2400 not in map
    assert _resolve_filename(spec, ctx) == "default.RData"


def test_resolve_filename_multi_key_miss_without_fallback_raises():
    ctx = {"pyear_end": 2400, "region": "ALL"}  # 2400 not in map, no filename field
    with pytest.raises(ValueError, match="emu-file"):
        _resolve_filename(MULTI_KEY_SPEC, ctx)


def test_resolve_filename_multi_key_miss_error_includes_valid_values():
    ctx = {"pyear_end": 2400, "region": "ALL"}
    with pytest.raises(ValueError, match="2300"):
        _resolve_filename(MULTI_KEY_SPEC, ctx)


def test_resolve_filename_multi_key_missing_first_key_returns_filename_fallback():
    """When pyear_end is absent, fall back to filename if present."""
    spec = dict(MULTI_KEY_SPEC, filename="default.RData")
    ctx = {"region": "ALL"}  # pyear_end missing
    assert _resolve_filename(spec, ctx) == "default.RData"


# ---------------------------------------------------------------------------
# from_module_schema — top_level_context seeding
# ---------------------------------------------------------------------------


def _make_schema_with_multi_key_input() -> ModuleSchema:
    return ModuleSchema(
        module_name="emulandice2-ais",
        container_image="test/image:latest",
        arguments={
            "inputs": [
                {
                    "name": "emu-file",
                    "source": "module_inputs.inputs.emu_file",
                    "optional": True,
                    "help": "Emulation file",
                    "filename_map": {
                        "keys": ["pyear_end", "region"],
                        "map": {
                            2300: {
                                "ALL": "AIS_ALL_2300.RData",
                                "WAIS": "AIS_WAIS_2300.RData",
                            },
                        },
                    },
                    "mount": {
                        "volume": "module_specific_input",
                        "container_path": "/mnt/in",
                    },
                }
            ],
            "options": [
                {
                    "name": "region",
                    "source": "module_inputs.options.region",
                    "optional": False,
                    "default_value": "ALL",
                }
            ],
            "outputs": {"files": [], "other": []},
            "top_level": [],
            "fingerprint_params": [],
        },
        volumes={},
    )


def test_from_module_schema_top_level_context_resolves_multi_key_filename():
    schema = _make_schema_with_multi_key_input()
    spec = ModuleExperimentSpec.from_module_schema(
        schema,
        prefilled_options={"region": ["ALL", "WAIS"]},
        top_level_context={"pyear_end": 2300, "pyear-end": 2300},
    )
    emu_file_bundle = spec.inputs.get("emu_file", {})
    assert emu_file_bundle.get("filename") == [
        "AIS_ALL_2300.RData",
        "AIS_WAIS_2300.RData",
    ]


def test_from_module_schema_top_level_context_lower_priority_than_schema_defaults():
    """top_level_context must not override schema option defaults."""
    schema = _make_schema_with_multi_key_input()
    # region default in schema is "ALL"; top_level_context should not clobber it
    spec = ModuleExperimentSpec.from_module_schema(
        schema,
        top_level_context={
            "pyear_end": 2300,
            "region": "WAIS",
        },  # region in top_level_context
        prefilled_options={"region": "ALL"},  # prefilled_options wins
    )
    assert spec.options.get("region") == "ALL"


# ---------------------------------------------------------------------------
# _options_defaults_from_schema
# ---------------------------------------------------------------------------


def test_options_defaults_empty_list():
    assert _options_defaults_from_schema([]) == {}


def test_options_defaults_extracts_default_value():
    specs = [{"name": "region", "default_value": "ALL", "source": "..."}]
    result = _options_defaults_from_schema(specs)
    assert result["region"] == "ALL"


def test_options_defaults_emits_both_case_forms():
    specs = [{"name": "pyear-end", "default_value": 2300}]
    result = _options_defaults_from_schema(specs)
    assert result["pyear-end"] == 2300
    assert result["pyear_end"] == 2300


def test_options_defaults_ignores_specs_without_default():
    specs = [{"name": "region", "source": "..."}]
    assert _options_defaults_from_schema(specs) == {}


# ---------------------------------------------------------------------------
# _build_section_from_fields — default_value propagation into bundle["value"]
# ---------------------------------------------------------------------------


def test_build_section_from_fields_propagates_default_value_to_value():
    """A field's default_value should populate bundle['value'] when nothing more
    specific is supplied, so it reaches the experiment-config as a real value."""
    fields = [
        {
            "name": "gesla-dir",
            "source": "module_inputs.inputs.gesla_dir",
            "default_value": "gesla_data_full",
        }
    ]
    result = _build_section_from_fields(fields)
    assert result["gesla_dir"]["value"] == "gesla_data_full"
    assert result["gesla_dir"]["default_value"] == "gesla_data_full"


def test_build_section_from_fields_prefilled_value_wins_over_default():
    fields = [
        {
            "name": "gesla-dir",
            "source": "module_inputs.inputs.gesla_dir",
            "default_value": "gesla_data_full",
        }
    ]
    result = _build_section_from_fields(
        fields, prefilled_values={"gesla_dir": "/custom/path"}
    )
    assert result["gesla_dir"]["value"] == "/custom/path"


def test_build_section_from_fields_no_default_leaves_value_none():
    fields = [{"name": "esl-data-path", "source": "module_inputs.inputs.esl_data_path"}]
    result = _build_section_from_fields(fields)
    assert result["esl_data_path"]["value"] is None
    assert "default_value" not in result["esl_data_path"]


# ---------------------------------------------------------------------------
# _build_options_context
# ---------------------------------------------------------------------------


def test_build_options_context_empty_inputs():
    assert _build_options_context({}, {}, {}) == {}


def test_build_options_context_priority_prefilled_over_schema_defaults():
    result = _build_options_context(
        schema_defaults={"region": "ALL"},
        prefilled_options={"region": "WAIS"},
        top_level_context={},
    )
    assert result["region"] == "WAIS"


def test_build_options_context_priority_schema_defaults_over_top_level():
    result = _build_options_context(
        schema_defaults={"region": "ALL"},
        prefilled_options={},
        top_level_context={"region": "WAIS"},
    )
    assert result["region"] == "ALL"


def test_build_options_context_kebab_prefilled_emits_snake_key():
    result = _build_options_context(
        schema_defaults={},
        prefilled_options={"pyear-end": 2300},
        top_level_context={},
    )
    assert result["pyear-end"] == 2300
    assert result["pyear_end"] == 2300


# ---------------------------------------------------------------------------
# _build_outputs
# ---------------------------------------------------------------------------


def test_build_outputs_empty():
    assert _build_outputs([], [], "my-module", {}) == {}


def test_build_outputs_file_output_prefixes_module_name():
    file_outputs = [
        {"name": "output-file", "filename": "out.nc", "output_type": "global"}
    ]
    result = _build_outputs(file_outputs, [], "my-module", {})
    assert result["output-file"]["value"] == "my-module/out.nc"
    assert result["output-file"]["output_type"] == "global"


def test_build_outputs_file_output_list_filename():
    file_outputs = [
        {
            "name": "output-file",
            "filename_map": {"region": {"EAIS": "eais.nc", "WAIS": "wais.nc"}},
            "output_type": "global",
        }
    ]
    result = _build_outputs(file_outputs, [], "my-module", {"region": "EAIS"})
    assert result["output-file"]["value"] == "my-module/eais.nc"


def test_build_outputs_raises_when_filename_missing():
    file_outputs = [{"name": "output-file", "output_type": "global"}]
    with pytest.raises(ValueError, match="missing.*filename"):
        _build_outputs(file_outputs, [], "my-module", {})


def test_build_outputs_raises_when_output_type_missing():
    file_outputs = [{"name": "output-file", "filename": "out.nc"}]
    with pytest.raises(ValueError, match="output_type"):
        _build_outputs(file_outputs, [], "my-module", {})


def test_build_outputs_other_output_uses_module_name():
    other_outputs = [
        {"name": "output-dir", "source": "module_inputs.outputs.output_dir"}
    ]
    result = _build_outputs([], other_outputs, "my-module", {})
    assert result["output-dir"] == {"value": "my-module"}
