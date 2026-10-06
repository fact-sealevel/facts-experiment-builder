import logging
from unittest.mock import patch

from click.testing import CliRunner

from facts_experiment_builder.cli.generate_compose_cli import (
    _ClickEchoHandler,
    _SUCCESS,
)

runner = CliRunner()


def test_click_echo_handler_success_includes_checkmark():
    handler = _ClickEchoHandler()
    record = logging.LogRecord(
        name="test",
        level=_SUCCESS,
        pathname="",
        lineno=0,
        msg="Created %s module",
        args=("my-module",),
        exc_info=None,
    )

    with patch(
        "facts_experiment_builder.cli.generate_compose_cli.console"
    ) as mock_console:
        handler.emit(record)

    mock_console.print.assert_called_once()
    printed = mock_console.print.call_args[0][0]
    assert "✓" in printed
    assert "[success]" in printed
    assert "Created my-module module" in printed


# def test_generate_compose_raises_error_with_invalid_config_path(tmp_path):
