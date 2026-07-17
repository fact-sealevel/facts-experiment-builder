from facts_experiment_builder.core.module.module_service_spec import (
    resolve_input_path,
)


def test_resolve_input_path_module_specific_field():
    """base dir already ends in module_name -> file joins directly under it"""
    result = resolve_input_path(
        field_name="a-file",
        field_value="data.nc",
        mount={"container_path": "/mnt/module_specific_in"},
        shared_input_data="/data/shared_input_data",
        module_specific_input_data="/data/module_specific_input_data",
        module_name="fair-temperature",
    )
    print("RESULT: ", result)

    assert result == "/data/module_specific_input_data/data.nc"


def test_resolve_input_path_shared_field_uses_shared_dir():
    result = resolve_input_path(
        field_name="location_file",
        field_value="location.lst",
        mount={"container_path": "/mnt/shared_in"},
        shared_input_data="/data/shared_input_data",
        module_specific_input_data="/data/module_specific_input_data",
        module_name="fair-temperature",
    )
    print("RESULT: ", result)
    assert result == "/data/shared_input_data/location.lst"


def test_resolve_input_path_base_dir_name_unrelated_to_module_name():
    result = resolve_input_path(
        field_name="some_file",
        field_value="data.nc",
        mount={"container_path": "/mnt/module_specific_in"},
        shared_input_data="/data/shared_input_data",
        module_specific_input_data="/data/module_specific_input_data/other-module",
        module_name="fair-temperature",
    )
    assert result == "/data/module_specific_input_data/other-module/data.nc"
