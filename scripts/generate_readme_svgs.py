#!/usr/bin/env python3
"""Generate SVG assets for the README from actual CLI Rich output.

Runs setup-experiment with the example command from the README,
captures the Rich-formatted terminal output, and writes SVGs to imgs/.

Usage:
    uv run python scripts/generate_readme_svgs.py
"""

import os
import shutil
import traceback
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from rich.console import Console

from facts_experiment_builder.cli.theme import lapaz_theme
from facts_experiment_builder.cli.setup_experiment_cli import main as setup_main
from facts_experiment_builder.cli.generate_compose_cli import main as compose_main

# ── README example command args ───────────────────────────────────────────────

SEALEVEL_MODULES = (
    "bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,"
    "ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,"
    "kopp14-verticallandmotion,ssp-landwaterstorage"
)

SETUP_ARGS = [
    "--experiment-name",
    "facts_experiment",
    "--climate-step",
    "fair-temperature",
    "--sealevel-step",
    SEALEVEL_MODULES,
    "--total-all-modules",
    "True",
    "--totaling-step",
    "facts-total",
    "--extremesealevel-step",
    "extremesealevel-pointsoverthreshold",
    "--pipeline-id",
    "aaa",
    "--scenario",
    "ssp126",
    "--baseyear",
    "2005",
    "--pyear-start",
    "2020",
    "--pyear-end",
    "2150",
    "--pyear-step",
    "10",
    "--nsamps",
    "1000",
    "--seed",
    "1234",
    "--location-file",
    "location.lst",
]

SETUP_COMMAND_LINES = [
    "uv run setup-experiment \\",
    "--experiment-name facts_experiment --climate-step fair-temperature \\",
    "--sealevel-step bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,kopp14-verticallandmotion,ssp-landwaterstorage \\",
    "--total-all-modules True --totaling-step facts-total \\",
    "--extremesealevel-step extremesealevel-pointsoverthreshold \\",
    "--pipeline-id aaa --scenario ssp126 --baseyear 2005 \\",
    "--pyear-start 2020 --pyear-end 2150 --pyear-step 10 \\",
    "--nsamps 1000 --seed 1234 --location-file location.lst",
]

DISPLAY_PREFIX = "./my-facts-project/"

IMGS_DIR = Path(__file__).parent.parent / "imgs"


def _make_recording_console(temp_prefix_ref: list) -> Console:
    """Return a recording Console whose print() replaces the temp path before recording.

    temp_prefix_ref is a one-element list so the prefix can be set after the
    isolated filesystem is entered (avoiding a chicken-and-egg problem).
    """
    console = Console(theme=lapaz_theme, record=True, width=220)
    _original_print = console.print

    def _print_with_path_replacement(*args, **kwargs):
        prefix = temp_prefix_ref[0]
        if prefix:
            args = tuple(
                arg.replace(prefix, DISPLAY_PREFIX) if isinstance(arg, str) else arg
                for arg in args
            )
        return _original_print(*args, **kwargs)

    console.print = _print_with_path_replacement
    return console


def generate_setup_svg() -> None:
    """Run setup-experiment and export the Rich output as an SVG."""
    temp_prefix_ref = [None]
    recording_console = _make_recording_console(temp_prefix_ref)

    for line in SETUP_COMMAND_LINES:
        recording_console.print(line, markup=False)

    prompt_answers = iter(
        ["wf1", "fittedismip-gris,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics"]
    )
    confirm_answers = iter([False])

    def mock_prompt(text, **kwargs):
        answer = next(prompt_answers)
        recording_console.print(f"{text}: {answer}", markup=False)
        return answer

    def mock_confirm(text, default=False, **kwargs):
        result = next(confirm_answers)
        recording_console.print(f"{text} [y/N]: {'y' if result else 'N'}", markup=False)
        return result

    runner = CliRunner()

    with runner.isolated_filesystem():
        temp_prefix_ref[0] = os.getcwd() + "/"
        os.makedirs("experiments")
        with (
            patch(
                "facts_experiment_builder.cli.setup_new_experiment_cli.console",
                recording_console,
            ),
            patch("click.prompt", mock_prompt),
            patch("click.confirm", mock_confirm),
        ):
            result = runner.invoke(setup_main, SETUP_ARGS, catch_exceptions=False)

    if result.exit_code != 0:
        print(f"CLI exited with code {result.exit_code}")
        print(result.output)
        if result.exception:
            traceback.print_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
        return

    svg = recording_console.export_svg(title="setup-experiment")
    out = IMGS_DIR / "cli_output_setup_new_experiment.svg"
    out.write_text(svg)
    print(f"Written: {out}")


def generate_compose_svg() -> None:
    """Run generate-compose against a complete experiment config and export SVG."""
    temp_prefix_ref = [None]
    recording_console = _make_recording_console(temp_prefix_ref)

    recording_console.print(
        "uv run generate-compose --experiment-name facts_experiment",
        markup=False,
    )

    runner = CliRunner()

    # coupling-ssp126 has all required paths filled in; facts_experiment does not.
    # We copy it into the isolated filesystem as facts_experiment so the
    # displayed experiment name in the SVG output remains correct.
    source_config = (
        Path(__file__).parent.parent
        / "experiments"
        / "coupling-ssp126"
        / "experiment-config.yaml"
    )

    with runner.isolated_filesystem():
        temp_prefix_ref[0] = os.getcwd() + "/"
        exp_dir = Path("experiments") / "facts_experiment"
        exp_dir.mkdir(parents=True)
        shutil.copy(source_config, exp_dir / "experiment-config.yaml")

        with patch(
            "facts_experiment_builder.cli.generate_compose_cli.console",
            recording_console,
        ):
            result = runner.invoke(
                compose_main,
                ["--experiment-name", "facts_experiment"],
                catch_exceptions=False,
            )

    if result.exit_code != 0:
        print(f"CLI exited with code {result.exit_code}")
        print(result.output)
        if result.exception:
            traceback.print_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
        return

    svg = recording_console.export_svg(title="generate-compose")
    out = IMGS_DIR / "cli_output_generate_compose.svg"
    out.write_text(svg)
    print(f"Written: {out}")


if __name__ == "__main__":
    IMGS_DIR.mkdir(exist_ok=True)
    generate_setup_svg()
    generate_compose_svg()
