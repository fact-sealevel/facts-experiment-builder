from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list,
)



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
