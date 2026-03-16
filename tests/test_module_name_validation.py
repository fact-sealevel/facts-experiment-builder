from facts_experiment_builder.core.registry import ModuleRegistry
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list,
    validate_module_names,
)

import pytest


def test_parse_module_list_comma_separated():
    input_module_list = "nzinsargps-verticallandmotion,kopp14-verticallandmotion,facts-total,extremesealevel-pointsoverthreshold"

    expected_parsed_module_list = [
        "nzinsargps-verticallandmotion",
        "kopp14-verticallandmotion",
        "facts-total",
        "extremesealevel-pointsoverthreshold",
    ]

    actual_parsed_module_list = parse_module_list(input_module_list)

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_parse_module_list_strips_whitespace():
    input_module_list = " ipccar5-icesheets, ipccar5-glaciers, fair-temperature "
    expected_parsed_module_list = [
        "ipccar5-icesheets",
        "ipccar5-glaciers",
        "fair-temperature",
    ]

    actual_parsed_module_list = parse_module_list(input_module_list)

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_parse_module_list_none_returns_empty():
    expected_parsed_module_list = []
    actual_parsed_module_list = parse_module_list(None)

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_parse_module_list_empty_string_returns_empty():
    expected_parsed_module_list = []
    actual_parsed_module_list = parse_module_list("")

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_validate_module_names_passes_for_valid():
    valid_module_names = ["fair-temperature", "ipccar5-icesheets", "ipccar5-glaciers"]
    validate_module_names(valid_module_names, ModuleRegistry.default().list_modules())


def test_validate_module_names_fails_for_invalid():
    invalid_module_names = ["invalid-module-name", "fair-temperature"]
    with pytest.raises(ValueError):
        validate_module_names(
            invalid_module_names,
            ModuleRegistry.default().list_modules(),
        )
