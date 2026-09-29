import pytest

from facts_experiment_builder.core.module.module_schema import ModuleContainerImage
from facts_experiment_builder.core.module.module_service_spec import (
    _parse_image,
    ModuleServiceSpecComponents,
    resolve_source_value,
)
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


def build_resolve_source_value_context():
    metadata_dict = {
        "experiment_name": "test experiment",
        "projection_scale": "local",
        "pipeline-id": "12345",
        "scenario": "ssp126",
        "nsamps": 50,
        "baseyear": 2005,
        "pyear_start": 2020,
        "pyear_end": 2150,
        "pyear_step": 10,
        "location-file": "location.lst",
        "climate_module": "module-name",
    }
    module_inputs = ModuleServiceSpecComponents(
        module_name="module-name",
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir="/module_specific_input",
            shared_input_dir="/shared_input_dir",
        ),
        output_paths=ModuleOutputPaths(
            output_dir="output",
            output_type="local",
        ),
        fingerprint_params={},
        inputs={},
        outputs={},
        image=ModuleContainerImage,
        output_container_base="output_container",
        metadata={},
    )
    return {"metadata": metadata_dict, "module_inputs": module_inputs}


def test_resolve_source_value_succeeds():
    context = build_resolve_source_value_context()

    pipeline_id_obj = resolve_source_value(
        source="metadata.pipeline-id", context=context
    )
    assert pipeline_id_obj == "12345"


def test_resolve_source_value_returns_none_if_no_source():
    obj = resolve_source_value(source="", context={})
    assert obj is None
