"""Pydantic models for module YAML argument spec components.

These models are the typed form of ModuleSchema.arguments. They catch unknown fields,
wrong types, missing required keys and malformed `source:` strings at YAML load time (in
ModuleSchema.from_dict).
"""

from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    InstanceOf,
    PlainSerializer,
)

from facts_experiment_builder.core.module.source_path import SourcePath


def _parse_source(value: Any) -> Any:
    return SourcePath.parse(value) if isinstance(value, str) else value


# A `source:` entry: parsed from its YAML string on load, and dumped
# back to that same string (so ModuleSchema.to_dict() round-trips).
SourceField = Annotated[
    InstanceOf[SourcePath],
    BeforeValidator(_parse_source),
    PlainSerializer(lambda s: s.raw, return_type=str),
]


class MountSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    container_path: str
    volume: str  # Optional[str] = None
    transform: str | None = None


class BaseArgSpec(BaseModel):
    """Fields shared by every argument spec, in every section."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: SourceField
    help: str | None = None
    optional: bool = False
    mount: MountSpec | None = None


class TopLevelArgSpec(BaseArgSpec):
    transform: str | None = None


class OptionArgSpec(BaseArgSpec):
    default_value: Any | None = None
    multiple: bool = False
    envvar: str | None = None
    allowed_values: list | None = None


class InputArgSpec(BaseArgSpec):
    filename: str | list | None = None
    filename_map: dict[str, Any] | None = None
    default_value: Any | None = None
    multiple: bool = False
    external_volume: bool = False
    # Set only on a sea-level module's climate input (whatever its CLI flag `name`,
    # e.g. climate-data-file or input-data-file): the climate step output it consumes.
    climate_step_output: str | None = None
    envvar: str | None = None


class OutputFileSpec(BaseArgSpec):
    filename: str | None = None
    filename_map: dict[str, Any] | None = None
    output_type: str
    pass_to_total: bool = True


class OtherOutputSpec(BaseArgSpec):
    pass


class OutputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[OutputFileSpec] = Field(default_factory=list)
    other: list[OtherOutputSpec] = Field(default_factory=list)


class FingerprintParamSpec(BaseArgSpec):
    filename: str | None = None
    default_value: str | None = None
    transform: str | None = None


class ArgumentsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_level: list[TopLevelArgSpec] = Field(default_factory=list)
    options: list[OptionArgSpec] = Field(default_factory=list)
    inputs: list[InputArgSpec] = Field(default_factory=list)
    outputs: OutputsSpec = Field(default_factory=OutputsSpec)
    fingerprint_params: list[FingerprintParamSpec] = Field(default_factory=list)


# Arg specs that can have a filename / filename_map (used when building the
# experiment-config.yaml section for a module).
FileArgSpec = InputArgSpec | FingerprintParamSpec | OutputFileSpec
