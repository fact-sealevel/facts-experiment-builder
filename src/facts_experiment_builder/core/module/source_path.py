"""Typed form of the dotted source strings used in module YAMLs.

`source:` and volume `host_path:` entries say where a value comes from when building a
compose service. Every one has one of these shapes:

metadata.<top-level param>            e.g. metadata.pipeline-id
module_inputs.<section>.<key>         e.g. module_inputs.inputs.rcmip_fname
module_inputs.<paths>.<attr>          e.g. module_inputs.input_paths.shared_input_dir
module_inputs.module_name

Parsing them once (at YAML load time) means a typo fails loudly instead of silently
resolving to None at compose time.
"""

from dataclasses import dataclass
from typing import Literal

from facts_experiment_builder.core.components.top_level_params import (
    TOP_LEVEL_PARAM_NAMES,
)

SourceRoot = Literal["metadata", "module_inputs"]

# ModuleServiceSpecComponents attributes addressable as module_inputs.<attr>.<key>
_KEYED_MODULE_INPUTS_ATTRS = frozenset(
    {
        "options",
        "inputs",
        "outputs",
        "fingerprint_params",
        "input_paths",
        "output_paths",
    }
)
# ModuleServiceSpecComponents attributes addressable as module_inputs.<attr>
_UNKEYED_MODULE_INPUTS_ATTRS = frozenset({"module_name"})


def _snake(part: str) -> str:
    return part.replace("-", "_")


@dataclass(frozen=True)
class SourcePath:
    """A parsed source string.

    `attr` is normalised to snake_case (it names a Python attribute). `key` is kept
    verbatim, because it is looked up in dicts whose keys may be kebab-case.
    """

    raw: str
    root: SourceRoot
    attr: str
    key: str | None = None

    @classmethod
    def parse(cls, raw: str) -> "SourcePath":
        """Parse a dotted source string, raising ValueError if it is malformed."""
        parts = raw.split(".")
        root = parts[0]

        if root == "metadata":
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid source '{raw}': expected 'metadata.<param>'."
                )
            attr = _snake(parts[1])
            if attr not in TOP_LEVEL_PARAM_NAMES:
                raise ValueError(
                    f"Invalid source '{raw}': unknown top-level param '{parts[1]}'. "
                    f"Expected one of {sorted(TOP_LEVEL_PARAM_NAMES)}."
                )
            return cls(raw=raw, root="metadata", attr=attr)

        if root == "module_inputs":
            attr = _snake(parts[1]) if len(parts) > 1 else ""
            if attr in _KEYED_MODULE_INPUTS_ATTRS and len(parts) == 3 and parts[2]:
                return cls(raw=raw, root="module_inputs", attr=attr, key=parts[2])
            if attr in _UNKEYED_MODULE_INPUTS_ATTRS and len(parts) == 2:
                return cls(raw=raw, root="module_inputs", attr=attr)
            raise ValueError(
                f"Invalid source '{raw}': expected 'module_inputs.<section>.<key>' with "
                f"section in {sorted(_KEYED_MODULE_INPUTS_ATTRS)}, or "
                f"'module_inputs.<attr>' with attr in {sorted(_UNKEYED_MODULE_INPUTS_ATTRS)}."
            )

        raise ValueError(
            f"Invalid source '{raw}': must start with 'metadata.' or 'module_inputs.'."
        )

    @property
    def leaf(self) -> str:
        """Last dotted segment, verbatim (e.g. 'rcmip_fname', 'pipeline-id')."""
        return self.raw.rsplit(".", 1)[-1]

    def __str__(self) -> str:
        return self.raw
