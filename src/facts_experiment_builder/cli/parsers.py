"""CLI input parsers: translate raw option strings into values for the application layer."""

from typing import List, Optional


def parse_comma_separated_modules(raw: Optional[str]) -> List[str]:
    """Parse a comma-separated string of module names into a list of non-empty strings.

    Intended for options like --sealevel-modules and --framework-modules.
    None or empty string yields an empty list. Whitespace around each name is stripped.

    Args:
        raw: Comma-separated module names, or None.

    Returns:
        List of stripped, non-empty module name strings.
    """
    if raw is None or not raw.strip():
        return []
    return [m.strip() for m in raw.split(",") if m.strip()]
