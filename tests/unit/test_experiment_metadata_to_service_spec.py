from facts_experiment_builder.application.experiment_metadata_to_service_spec import (
    module_type_is_valid,
)
import pytest
# def test_module_type_is_valid_is_true_when_type_is_none():
#     module_type = None

#     result = module_type_is_valid(module_type=module_type)
#     assert result == True


@pytest.mark.parametrize(
    "mod_type, expected",
    [
        (None, True),
        ("sealevel_module", True),
        ("temperature_module", True),
        ("framework_module", True),
        ("extreme_sealevel_module", True),
        ("other_module", True),
    ],
)
def test_module_type_is_valid(mod_type, expected):
    assert module_type_is_valid(mod_type) is expected
