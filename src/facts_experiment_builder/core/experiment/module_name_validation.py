def parse_module_list(s: str | None) -> list[str]:
    """Parse a comma-separated string of module names into a list of stripped names"""

    if not s:
        return []
    return [m.strip() for m in s.split(",") if m.strip()]


def validate_module_names(module_names: list[str], valid_modules: set[str]) -> None:
    """Raise ValueError if any module name is not in the valid set"""
    invalid_names = [name for name in module_names if name not in valid_modules]
    if invalid_names:
        raise ValueError(f"Invalid module name(s): {', '.join(invalid_names)}.")
