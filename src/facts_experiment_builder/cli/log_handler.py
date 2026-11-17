"""Log handler that prints facts_experiment_builder log records to the CLI console."""

import logging

from facts_experiment_builder.application.log_levels import SUCCESS
from facts_experiment_builder.cli.theme import console


class ClickEchoHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if record.levelno >= logging.WARNING:
            console.print(f"⚠ [danger]Warning: [/danger]{msg}")
        elif record.levelno == SUCCESS:
            console.print(f"✓ [success]{msg}[/success]")
        else:  # INFO
            console.print(f"ℹ [accent]{msg}[/accent]")


def configure_feb_logging() -> None:
    """Wire the ClickEchoHandler onto the facts_experiment_builder namespace logger.

    Called at CLI invocation time (not import time) so that tests importing from sibling
    modules don't accidentally install the handler and break caplog capture.
    """
    feb_logger = logging.getLogger("facts_experiment_builder")
    if not any(isinstance(h, ClickEchoHandler) for h in feb_logger.handlers):
        feb_logger.addHandler(ClickEchoHandler())
    feb_logger.setLevel(logging.INFO)
    feb_logger.propagate = False
