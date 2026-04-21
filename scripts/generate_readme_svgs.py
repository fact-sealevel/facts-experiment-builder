#!/usr/bin/env python3
"""Generate SVG assets for the README from actual CLI Rich output.

Runs setup-new-experiment with the example command from the README,
captures the Rich-formatted terminal output, and writes SVGs to imgs/.

Usage:
    uv run python scripts/generate_readme_svgs.py
"""

import os
import re
import shutil
import traceback
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from rich.console import Console

from facts_experiment_builder.cli.theme import lapaz_theme
from facts_experiment_builder.cli.setup_new_experiment_cli import main as setup_main
from facts_experiment_builder.cli.generate_compose_cli import main as compose_main

# ── README example command args ───────────────────────────────────────────────

SEALEVEL_MODULES = (
    "bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,"
    "ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,"
    "kopp14-verticallandmotion,ssp-landwaterstorage"
)

SETUP_ARGS = [
    "--experiment-name", "facts_experiment",
    "--climate-step", "fair-temperature",
    "--sealevel-step", SEALEVEL_MODULES,
    "--total-all-modules", "True",
    "--totaling-step", "facts-total",
    "--extremesealevel-step", "extremesealevel-pointsoverthreshold",
    "--pipeline-id", "aaa",
    "--scenario", "ssp126",
    "--baseyear", "2005",
    "--pyear-start", "2020",
    "--pyear-end", "2150",
    "--pyear-step", "10",
    "--nsamps", "1000",
    "--seed", "1234",
    "--location-file", "location.lst",
]

# Command text shown at the top of the setup SVG, matching the README example
SETUP_COMMAND_LINES = [
    "uv run setup-new-experiment \\",
    "--experiment-name facts_experiment --climate-step fair-temperature \\",
    "--sealevel-step bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,kopp14-verticallandmotion,ssp-landwaterstorage \\",
    "--total-all-modules True --totaling-step facts-total \\",
    "--extremesealevel-step extremesealevel-pointsoverthreshold \\",
    "--pipeline-id aaa --scenario ssp126 --baseyear 2005 \\",
    "--pyear-start 2020 --pyear-end 2150 --pyear-step 10 \\",
    "--nsamps 1000 --seed 1234 --location-file location.lst",
]

IMGS_DIR = Path(__file__).parent.parent / "imgs"


def _strip_textlength(svg: str) -> str:
    """Remove SVG textLength attributes that cause Rich to letter-space overflowing lines."""
    return re.sub(r'\s*textLength="[^"]*"', "", svg)


def generate_setup_svg() -> None:
    """Run setup-new-experiment and export the Rich output as an SVG."""
    recording_console = Console(theme=lapaz_theme, record=True, width=220)

    # Print the command at the top so the SVG shows what was run
    for line in SETUP_COMMAND_LINES:
        recording_console.print(line, markup=False)

    # --total-all-modules True auto-creates the "all-modules" workflow, but the
    # while loop still prompts for at least one additional workflow before asking
    # whether to continue. We simulate one minimal extra workflow then decline.
    prompt_answers = iter(["wf1", "fittedismip-gris,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics"])
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

    temp_prefix = None
    with runner.isolated_filesystem():
        temp_prefix = os.getcwd() + "/"
        os.makedirs("experiments")
        with (
            patch(
                "facts_experiment_builder.cli.setup_new_experiment_cli.console",
                recording_console,
            ),
            patch("click.prompt", mock_prompt),
            patch("click.confirm", mock_confirm),
        ):
            result = runner.invoke(
                setup_main,
                SETUP_ARGS,
                catch_exceptions=False,
            )

    if result.exit_code != 0:
        print(f"CLI exited with code {result.exit_code}")
        print(result.output)
        if result.exception:
            traceback.print_exception(
                type(result.exception),
                result.exception,
                result.exception.__traceback__,
            )
        return

    svg = recording_console.export_svg(title="setup-new-experiment")
    svg = svg.replace(temp_prefix, "./my-facts-project/")
    svg = _strip_textlength(svg)
    out = IMGS_DIR / "cli_output_setup_new_experiment.svg"
    out.write_text(svg)
    print(f"Written: {out}")


def generate_compose_svg() -> None:
    """Run generate-compose against the checked-in facts_experiment and export SVG."""
    recording_console = Console(theme=lapaz_theme, record=True, width=220)

    recording_console.print(
        "uv run generate-compose --experiment-name facts_experiment",
        markup=False,
    )

    runner = CliRunner()

    source_config = (
        Path(__file__).parent.parent
        / "experiments" / "facts_experiment" / "experiment-config.yaml"
    )

    temp_prefix = None

    with runner.isolated_filesystem():
        temp_prefix = os.getcwd() + "/"
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
                type(result.exception),
                result.exception,
                result.exception.__traceback__,
            )
        return

    svg = recording_console.export_svg(title="generate-compose")
    svg = svg.replace(temp_prefix, "./my-facts-project/")
    svg = _strip_textlength(svg)
    out = IMGS_DIR / "cli_output_generate_compose.svg"
    out.write_text(svg)
    print(f"Written: {out}")


if __name__ == "__main__":
    IMGS_DIR.mkdir(exist_ok=True)
    generate_setup_svg()
    generate_compose_svg()
