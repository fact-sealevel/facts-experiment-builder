from facts_experiment_builder.io.write_config import (
    format_module_value,
)


def test_format_module_value_returns_correct_when_value_is_nested_dict():
    key = "rcmip_concentration_fname"
    value = {
        "clue": "clue about this input obj",
        "value": None,
        "filename": "/path/to/file",
    }
    indent = 2

    formatted = format_module_value(key=key, value=value, indent=indent)
    print(formatted)
    assert formatted == [
        "  rcmip_concentration_fname:",
        "    # clue about this input obj",
        '    "/path/to/file"  # filename from module defaults',
    ]
