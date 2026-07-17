"""Tests for arg_specs Pydantic models and ArgumentsSpec validation in ModuleSchema."""

import pytest
from pydantic import ValidationError

from facts_experiment_builder.core.module.arg_specs import (
    ArgumentsSpec,
    InputArgSpec,
    MountSpec,
    OptionArgSpec,
    OtherOutputSpec,
    OutputFileSpec,
    OutputsSpec,
    TopLevelArgSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema


# ---------------------------------------------------------------------------
# MountSpec
# ---------------------------------------------------------------------------


def test_mount_spec_shared_in_doesnt_have_transform(mount_spec_shared_in):
    assert mount_spec_shared_in.transform is None


def test_mount_spec_shared_in_is_input_volume(mount_spec_shared_in):
    assert mount_spec_shared_in.volume == "input"


def test_mount_spec_module_specific_in_is_input_volume(mount_spec_module_specific_in):
    assert mount_spec_module_specific_in.volume == "input"


def test_mount_spec_minimal(mount_spec_out):
    assert mount_spec_out.volume == "output"
    assert mount_spec_out.transform is None


def test_mount_spec_full():
    m = MountSpec(volume="output", container_path="/mnt/out", transform="filename")
    assert m.volume == "output"


def test_mount_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        MountSpec(container_path="/mnt/out", unknown_key="x")


# ---------------------------------------------------------------------------
# TopLevelArgSpec
# ---------------------------------------------------------------------------


def test_top_level_arg_spec_required_fields():
    spec = TopLevelArgSpec(name="scenario", type="str", source="metadata.scenario")
    assert spec.optional is False
    assert spec.mount is None
    assert spec.alternatives == []


def test_top_level_arg_spec_with_mount(mount_spec_shared_in):
    spec = TopLevelArgSpec(
        name="location-file",
        type="str",
        source="metadata.location-file",
        optional=True,
        help="Location file path",
        transform="filename",
        mount=mount_spec_shared_in,
    )
    assert spec.mount.container_path == "/mnt/shared_in"


def test_top_level_arg_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        TopLevelArgSpec(name="x", type="str", source="metadata.x", bogus=True)


# ---------------------------------------------------------------------------
# OptionArgSpec
# ---------------------------------------------------------------------------


def test_option_arg_spec_defaults():
    spec = OptionArgSpec(name="seed", type="int", source="module_inputs.options.seed")
    assert spec.multiple is False
    assert spec.envvar is None
    assert spec.default_value is None


def test_option_arg_spec_with_default_value():
    spec = OptionArgSpec(
        name="seed", type="int", source="module_inputs.options.seed", default_value=1234
    )
    assert spec.default_value == 1234


def test_option_arg_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        OptionArgSpec(name="x", type="int", source="s", extra_field="bad")


# ---------------------------------------------------------------------------
# InputArgSpec
# ---------------------------------------------------------------------------


def test_input_arg_spec_minimal(random_module_specific_inputs_arg_spec):
    spec = random_module_specific_inputs_arg_spec
    assert spec.mount is not None
    assert spec.climate_step_output is None
    assert spec.name is not None
    assert spec.type == "file"


def test_module_specific_input_has_source_module_inputs(
    random_module_specific_inputs_arg_spec,
):
    spec = random_module_specific_inputs_arg_spec

    assert spec.source.startswith("module_inputs.inputs")


def test_input_arg_spec_climate_step_output(climate_data_file_arg_spec):
    spec = climate_data_file_arg_spec
    assert spec.climate_step_output == "output-climate-file"


def test_input_arg_spec_with_mount(mount_spec_module_specific_in):
    spec = mount_spec_module_specific_in
    assert spec.volume == "input"
    assert spec.container_path == "/mnt/module_specific_in"


def test_input_arg_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        InputArgSpec(name="x", type="file", source="s", unknown="y")


def test_input_arg_spec_for_dir_has_correct_type(non_file_input_arg_spec):
    spec = non_file_input_arg_spec
    assert spec.name == "zosdir"
    assert spec.type == "dir"


# ---------------------------------------------------------------------------
# OutputFileSpec
# ---------------------------------------------------------------------------


def test_output_file_spec_defaults():
    spec = OutputFileSpec(
        name="output-gslr-file",
        type="file",
        source="module_inputs.outputs.output_gslr_file",
        output_type="global",
    )
    assert spec.pass_to_total is True
    assert spec.optional is False


def test_output_file_spec_pass_to_total():
    spec = OutputFileSpec(
        name="output-gslr-file",
        type="file",
        source="module_inputs.outputs.output_gslr_file",
        output_type="global",
        pass_to_total=True,
    )
    assert spec.pass_to_total is True


def test_output_file_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        OutputFileSpec(
            name="x", type="file", source="s", output_type="global", bad_field=1
        )


# ---------------------------------------------------------------------------
# OtherOutputSpec
# ---------------------------------------------------------------------------


def test_other_output_spec_minimal():
    spec = OtherOutputSpec(
        name="output-glacier-dir",
        type="str",
        source="module_inputs.outputs.output_glacier_dir",
    )
    assert spec.optional is False


# ---------------------------------------------------------------------------
# OutputsSpec
# ---------------------------------------------------------------------------


def test_outputs_spec_empty_defaults():
    spec = OutputsSpec()
    assert spec.files == []
    assert spec.other == []


def test_outputs_spec_rejects_unknown_section():
    with pytest.raises(ValidationError):
        OutputsSpec(files=[], unknown_section=[])


# ---------------------------------------------------------------------------
# ArgumentsSpec
# ---------------------------------------------------------------------------


def test_arguments_spec_empty_is_valid():
    spec = ArgumentsSpec()
    assert spec.top_level == []
    assert spec.inputs == []
    assert spec.outputs.files == []


def test_arguments_spec_rejects_unknown_section():
    with pytest.raises(ValidationError):
        ArgumentsSpec(not_a_real_section=[])


def test_arguments_spec_full_round_trip():
    data = {
        "top_level": [
            {"name": "scenario", "type": "str", "source": "metadata.scenario"}
        ],
        "options": [
            {"name": "seed", "type": "int", "source": "module_inputs.options.seed"}
        ],
        "inputs": [
            {
                "name": "climate-data-file",
                "type": "file",
                "source": "module_inputs.inputs.climate_data_file",
                "mount": {"volume": "output", "container_path": "/mnt/out"},
                "external_volume": True,
                "climate_step_output": "fair-temperature",
            }
        ],
        "outputs": {
            "files": [
                {
                    "name": "output-gslr-file",
                    "type": "file",
                    "source": "module_inputs.outputs.output_gslr_file",
                    "output_type": "global",
                    "filename": "gslr.nc",
                    "pass_to_total": True,
                    "mount": {"volume": "output", "container_path": "/mnt/out"},
                }
            ]
        },
        "fingerprint_params": [],
    }
    spec = ArgumentsSpec(**data)
    assert spec.inputs[0].climate_step_output == "fair-temperature"
    assert spec.outputs.files[0].pass_to_total is True


# ---------------------------------------------------------------------------
# ModuleSchema.from_dict integration
# ---------------------------------------------------------------------------


def test_from_dict_validates_arguments():
    """from_dict raises ValidationError for unknown argument spec fields."""
    with pytest.raises(ValidationError):
        ModuleSchema.from_dict(
            {
                "module_name": "test",
                "container_image": "img:tag",
                "arguments": {
                    "inputs": [
                        {
                            "name": "x",
                            "type": "file",
                            "source": "s",
                            "not_a_real_field": True,
                        }
                    ]
                },
                "volumes": {},
            }
        )


def test_from_dict_accepts_valid_arguments():
    schema = ModuleSchema.from_dict(
        {
            "module_name": "test",
            "container_image": "img:tag",
            "arguments": {
                "inputs": [
                    {
                        "name": "climate-data-file",
                        "type": "file",
                        "source": "module_inputs.inputs.climate_data_file",
                        "climate_step_output": "fair-temperature",
                    }
                ],
                "outputs": {
                    "files": [
                        {
                            "name": "output-gslr-file",
                            "type": "file",
                            "source": "module_inputs.outputs.output_gslr_file",
                            "output_type": "global",
                            "pass_to_total": False,
                        }
                    ]
                },
            },
            "volumes": {},
        }
    )
    assert schema.module_name == "test"
