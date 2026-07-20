from typing import List


def parse_module_list_str(s: str | None) -> list[str]:
    """Parse a comma-separated string of module names into a list of stripped names."""
    if s is not None and not isinstance(s, str):
        raise TypeError(f"Expected str or None, got {type(s)}")
    if not s:
        return []
    return [m.strip() for m in s.split(",") if m.strip()]


def unparse_module_list(modules: List[str]) -> str | None:
    """Convert a list of module names into a comma-separated string."""
    if not isinstance(modules, List):
        raise TypeError(f"Expected list, got {type(modules)}")
    if not modules:
        return None
    return ", ".join(modules)


def validate_module_names(module_names: List[str], valid_modules: set[str]) -> None:
    """Raise ValueError if any module name is not in the valid set."""
    invalid_names = [name for name in module_names if name not in valid_modules]
    if invalid_names:
        raise ValueError(f"Invalid module name(s): {', '.join(invalid_names)}.")
