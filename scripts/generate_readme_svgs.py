#!/usr/bin/env python3
"""Generate SVG assets for the README from actual CLI Rich output.

Runs setup-new-experiment with the example command from the README,
captures the Rich-formatted terminal output, and writes SVGs to imgs/.

Usage:
    uv run python scripts/generate_readme_svgs.py
"""

import os
import traceback
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from rich.console import Console

from facts_experiment_builder.cli.theme import lapaz_theme
from facts_experiment_builder.cli.setup_new_experiment_cli import main as setup_main

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

IMGS_DIR = Path(__file__).parent.parent / "imgs"

def generate_setup_svg() -> None:
    """Run setup-new-experiment and export the Rich output as an SVG."""
    recording_console = Console(theme=lapaz_theme, record=True, width=120)

    # --total-all-modules True auto-creates the "all-modules" workflow, but the
    # while loop still prompts for at least one additional workflow before asking
    # whether to continue. We simulate one minimal extra workflow then decline.
    prompt_answers = iter(["wf1", "ipccar5-icesheets,tlm-sterodynamics"])
    confirm_answers = iter([False])

    def mock_prompt(text, **kwargs):
        answer = next(prompt_answers)
        recording_console.print(f"{text}: {answer}")
        return answer

    def mock_confirm(text, default=False, **kwargs):
        result = next(confirm_answers)
        recording_console.print(f"{text} [y/N]: {'y' if result else 'N'}")
        return result

    runner = CliRunner()

    with runner.isolated_filesystem():
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
    out = IMGS_DIR / "cli_output_setup_new_experiment.svg"
    out.write_text(svg)
    print(f"Written: {out}")


if __name__ == "__main__":
    IMGS_DIR.mkdir(exist_ok=True)
    generate_setup_svg()
