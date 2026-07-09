from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
    unparse_module_list,
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

    actual_parsed_module_list = parse_module_list_str(input_module_list)

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_parse_module_list_fails_if_str_not_received():
    module_ls = ["module-name", "module-name1", "module-name2"]
    with pytest.raises(TypeError):
        parse_module_list_str(module_ls)


def test_parse_module_list_strips_whitespace():
    input_module_list = " ipccar5-icesheets, ipccar5-glaciers, fair-temperature "
    expected_parsed_module_list = [
        "ipccar5-icesheets",
        "ipccar5-glaciers",
        "fair-temperature",
    ]

    actual_parsed_module_list = parse_module_list_str(input_module_list)

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_parse_module_list_none_returns_empty():
    expected_parsed_module_list = []
    actual_parsed_module_list = parse_module_list_str(None)

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_parse_module_list_empty_string_returns_empty():
    expected_parsed_module_list = []
    actual_parsed_module_list = parse_module_list_str("")

    assert actual_parsed_module_list == expected_parsed_module_list, (
        f"parse_module_list should return {expected_parsed_module_list}, instead received {actual_parsed_module_list}"
    )


def test_unparse_module_list_fails_if_str_received():
    module_str = "bamber19-icesheets,deconto21-ais,fair-temperature"

    with pytest.raises(TypeError):
        unparse_module_list(module_str)
