from facts_experiment_builder.core.module.module_service_spec import _parse_image
from facts_experiment_builder.core.module.module_schema import ModuleContainerImage
import pytest


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
