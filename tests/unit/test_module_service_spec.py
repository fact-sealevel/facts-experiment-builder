import pytest

from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.module.module_schema import ModuleContainerImage
from facts_experiment_builder.core.module.module_service_spec import (
    _parse_image,
    ModuleServiceSpecComponents,
)
from facts_experiment_builder.core.module.source_path import SourcePath
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
)


def test_input_arg_spec_by_key_returns_correct_spec():
    NotImplementedError


def test_parse_image_string_with_tag():
    result = _parse_image("ghcr.io/example/image:v1.2", "test module")
    assert result == ModuleContainerImage(
        image_url="ghcr.io/example/image", image_tag="v1.2"
    )


def test_parse_image_raises_error_with_no_tag():
    string = "ghcr.io/example/image"
    module_context = "test module"
    with pytest.raises(ValueError):
        _parse_image(image_data=string, module_context=module_context)


def test_parse_image_non_string_raises():
    image_dict = {"image_url": "some url", "another key": "another val"}
    module_context = "test module"
    with pytest.raises(ValueError):
        _parse_image(image_data=image_dict, module_context=module_context)


@pytest.fixture
def resolve_components():
    return ModuleServiceSpecComponents(
        module_name="module-name",
        options={"seed": 1234},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir="/module_specific_input",
            shared_input_dir="/shared_input_dir",
        ),
        output_paths=ModuleOutputPaths(
            output_dir="output",
            output_type="local",
        ),
        fingerprint_params={"location_file": "location.lst"},
        inputs={"climate_data_file": "fair-temperature/climate.nc"},
        outputs={},
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        output_container_base="output_container",
        top_level_params=TopLevelParams.from_config(
            {
                "experiment_name": "test experiment",
                "pipeline-id": "12345",
                "scenario": "ssp126",
                "nsamps": 50,
                "location-file": "location.lst",
            }
        ),
    )


def test_top_level_params_from_config_reads_kebab_and_snake_keys():
    params = TopLevelParams.from_config({"pipeline-id": "abc", "pyear_end": 2100})
    assert params.pipeline_id == "abc"
    assert params.pyear_end == 2100
    assert params.baseyear is None


def test_resolve_metadata_param(resolve_components):
    source = SourcePath.parse("metadata.pipeline-id")
    assert resolve_components.resolve(source) == "12345"


def test_resolve_metadata_param_missing_from_config_is_none(resolve_components):
    assert resolve_components.resolve(SourcePath.parse("metadata.baseyear")) is None


def test_resolve_module_inputs_section_key(resolve_components):
    source = SourcePath.parse("module_inputs.inputs.climate_data_file")
    assert resolve_components.resolve(source) == "fair-temperature/climate.nc"


def test_resolve_module_inputs_kebab_key_falls_back_to_snake(resolve_components):
    source = SourcePath.parse("module_inputs.inputs.climate-data-file")
    assert resolve_components.resolve(source) == "fair-temperature/climate.nc"


def test_resolve_module_inputs_missing_key_is_none(resolve_components):
    source = SourcePath.parse("module_inputs.options.not_provided")
    assert resolve_components.resolve(source) is None


def test_resolve_module_inputs_paths_attr(resolve_components):
    source = SourcePath.parse("module_inputs.input_paths.shared_input_dir")
    assert resolve_components.resolve(source) == "/shared_input_dir"


def test_resolve_module_name(resolve_components):
    source = SourcePath.parse("module_inputs.module_name")
    assert resolve_components.resolve(source) == "module-name"


@pytest.mark.parametrize(
    "raw, root, attr, key",
    [
        ("metadata.pipeline-id", "metadata", "pipeline_id", None),
        ("metadata.pyear_end", "metadata", "pyear_end", None),
        ("module_inputs.inputs.rcmip-file", "module_inputs", "inputs", "rcmip-file"),
        (
            "module_inputs.fingerprint-params.fp_file",
            "module_inputs",
            "fingerprint_params",
            "fp_file",
        ),
        (
            "module_inputs.fingerprint_params.fp_file",
            "module_inputs",
            "fingerprint_params",
            "fp_file",
        ),
        ("module_inputs.module_name", "module_inputs", "module_name", None),
    ],
)
def test_source_path_parse_valid(raw, root, attr, key):
    source = SourcePath.parse(raw)
    assert (source.root, source.attr, source.key, source.raw) == (root, attr, key, raw)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "metadata",
        "metadata.not_a_param",
        "metadata.pipeline-id.extra",
        "module_inputs.output.x",
        "module_inputs.inputs",
        "module_inputs.inputs.",
        "module_inputs.module_name.extra",
        "module_inpputs.inputs.x",
        "external.some_volume",
    ],
)
def test_source_path_parse_invalid_raises(raw):
    with pytest.raises(ValueError):
        SourcePath.parse(raw)


def test_source_path_leaf_keeps_yaml_spelling():
    assert SourcePath.parse("metadata.location-file").leaf == "location-file"
