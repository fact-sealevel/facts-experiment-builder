"""Shared Rich theme and console for facts-experiment-builder CLI output.

Mid-range lapaz colormap stops — visible on both light and dark terminals. Avoids the
near-black (#190B35) and near-white (#F9F3C5) extremes.
"""

from rich.console import Console
from rich.theme import Theme
from rich.markup import escape
import logging

lapaz_theme = Theme(
    {
        "primary": "bold #1E6896",  # lapaz_25 — royal blue, high contrast on both
        "secondary": "#228B8D",  # lapaz_50 — teal, solid mid-tone
        "accent": "#5AADA8",  # lapaz_40ish — slightly lighter teal
        "success": "#82C8A0",  # lapaz_75 — sage green, readable on dark/mid BGs
        "muted": "#4A7FA5",  # slightly desaturated blue — safe mid-tone
        "rule": "#228B8D",  # teal rule lines
        "warning": "bold #C4A862",  # warm gold — visible on both (not in lapaz but complements it)
        "danger": "bold #C0504A",  # muted red — universal danger signal
    }
)

console = Console(theme=lapaz_theme)

GLYPHS = {
    logging.DEBUG: ("·", "secondary"),
    logging.INFO: ("\u2713success"),
    logging.WARNING: ("\u0021", "warning"),
    logging.ERROR: ("\u2717", "error"),
    logging.CRITICAL: ("u/2717", "error"),
}


class RichConsoleHandler(logging.Handler):
    def __init__(self, console: Console):
        super().__init__()
        self.console = console

    def emit(self, record):
        try:
            glyph, style = GLYPHS.get(record.levelno, ("·", "secondary"))
            out = f"[{style}]{glyph} {escape(self.format(record))}[/{style}]"
            detail = getattr(record, "detail", None)
            if detail is not None:
                out += f" [secondary]{escape(str(detail))}[/secondary]"
            self.console.print(out)
        except Exception:
            self.handleError(record)
