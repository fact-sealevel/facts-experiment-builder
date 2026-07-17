from dataclasses import dataclass
from typing import Literal
from pathlib import Path
import os

ModuleOutputType = Literal["local", "global", "total", "esl"]


@dataclass(frozen=True)
class ModuleInputPaths:
    """Input paths for a module: module-specific and general dirs, plus resolved input_dir."""

    input_dir: str
    module_specific_input_dir: str
    shared_input_dir: str


@dataclass(frozen=True)
class ModuleOutputPaths:
    """Output paths for a module."""

    output_dir: str
    output_type: ModuleOutputType


def _resolve_module_input_dir(module_specific_input_dir: str, module_name: str) -> str:
    """Resolve the effective module input directory from base path and module name."""
    if not module_name or not module_specific_input_dir:
        return module_specific_input_dir
    try:
        base_path = Path(module_specific_input_dir)
    except TypeError as e:
        raise ValueError(
            f"Cannot create Path from module_specific_input_dir for {module_name}: "
            f"module_specific_input_dir={module_specific_input_dir!r}, type={type(module_specific_input_dir)}"
        ) from e
    if base_path.name == module_name:
        return module_specific_input_dir
    # Multi-command module: path already points at shared dir (e.g. .../ipccar5); do not append module_name.
    if base_path.name and module_name.startswith(base_path.name + "-"):
        return module_specific_input_dir
    if base_path.name:
        return str(base_path.parent / module_name)
    return os.path.join(module_specific_input_dir, module_name)


def build_module_input_paths(
    *,
    module_specific_input_dir: str = "",
    shared_input_dir: str = "",
    module_name: str = "",
) -> ModuleInputPaths:
    """Build and validate ModuleInputPaths. Raises ValueError if invalid."""
    if module_specific_input_dir is None:
        raise ValueError(
            f"module_specific_input_dir is None when building paths for {module_name}."
        )
    if module_specific_input_dir != "" and not isinstance(
        module_specific_input_dir, str
    ):
        raise ValueError(
            f"module_specific_input_dir has invalid type for {module_name}: expected str, got {type(module_specific_input_dir)}"
        )
    if shared_input_dir is None:
        raise ValueError(
            f"shared_input_dir is None when building paths for {module_name}."
        )
    if shared_input_dir != "" and not isinstance(shared_input_dir, str):
        raise ValueError(
            f"shared_input_dir has invalid type for {module_name}: expected str, got {type(shared_input_dir)}"
        )
    ms = module_specific_input_dir or ""
    gen = shared_input_dir or ""
    input_dir = _resolve_module_input_dir(ms, module_name)
    return ModuleInputPaths(
        input_dir=input_dir,
        module_specific_input_dir=ms,
        shared_input_dir=gen,
    )


def build_module_output_paths(
    output_dir: str, output_type: ModuleOutputType, module_name: str = ""
) -> ModuleOutputPaths:
    """Build and validate ModuleOutputPaths. Raises ValueError if invalid."""
    if output_dir is None:
        raise ValueError(
            f"output_dir is None when building paths for {module_name}. "
            "This usually means 'output-data-location' path is None in metadata."
        )
    if not isinstance(output_dir, str):
        raise ValueError(
            f"output_dir has invalid type for {module_name}: expected str, got {type(output_dir)}"
        )
    return ModuleOutputPaths(output_dir=output_dir, output_type=output_type)
