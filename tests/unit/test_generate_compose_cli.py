import logging
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from facts_experiment_builder.cli.generate_compose_cli import (
    _ClickEchoHandler,
    _SUCCESS,
    main,
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


def test_custom_compose_path_is_passed_as_a_path(tmp_path):
    """--custom-compose-path reaches generate_compose() as a Path, which it resolves."""
    custom = tmp_path / "custom" / "experiment-compose.yaml"
    custom.parent.mkdir()

    with (
        patch(
            "facts_experiment_builder.cli.generate_compose_cli.generate_compose"
        ) as mock_generate,
        patch("facts_experiment_builder.cli.generate_compose_cli.write_compose_yaml"),
    ):
        mock_generate.return_value.compose_dict = {"services": {}}
        mock_generate.return_value.compose_path = Path.cwd() / "experiment-compose.yaml"
        result = runner.invoke(
            main,
            [
                "--experiment-name",
                "exp",
                "--workspace-dir",
                str(tmp_path),
                "--custom-compose-path",
                str(custom),
            ],
        )

    assert result.exit_code == 0, result.output
    passed = mock_generate.call_args.kwargs["custom_compose_path"]
    assert isinstance(passed, Path)
    assert passed == custom


# def test_generate_compose_raises_error_with_invalid_config_path(tmp_path):
