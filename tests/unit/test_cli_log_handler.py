import logging
from unittest.mock import patch

from facts_experiment_builder.application.log_levels import SUCCESS
from facts_experiment_builder.cli.log_handler import ClickEchoHandler


def test_click_echo_handler_success_includes_checkmark():
    handler = ClickEchoHandler()
    record = logging.LogRecord(
        name="test",
        level=SUCCESS,
        pathname="",
        lineno=0,
        msg="Created %s module",
        args=("my-module",),
        exc_info=None,
    )

    with patch("facts_experiment_builder.cli.log_handler.console") as mock_console:
        handler.emit(record)

    mock_console.print.assert_called_once()
    printed = mock_console.print.call_args[0][0]
    assert "✓" in printed
    assert "[success]" in printed
    assert "Created my-module module" in printed
