"""Pydantic models for module YAML argument spec components.

These models validate the structure of dicts inside ModuleSchema.arguments — catching
unknown fields, wrong types, and missing required keys at YAML load time (in
ModuleSchema.from_dict).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MountSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    container_path: str
    volume: str  # Optional[str] = None
    transform: str | None = None


class TopLevelArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    optional: bool = False
    help: str | None = None
    transform: str | None = None
    mount: MountSpec | None = None
    alternatives: list[str] = Field(default_factory=list)


class OptionArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    optional: bool = False
    help: str | None = None
    default_value: Any | None = None
    multiple: bool = False
    envvar: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    allowed_values: list | None = None
    mount: MountSpec | None = None  # needed for extremesealevel-pointsoverthreshold


class InputArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    help: str | None = None
    filename: str | list = None
    filename_map: dict[str, Any] | None = None
    default_value: Any | None = None
    optional: bool = False
    multiple: bool = False
    external_volume: bool = False
    mount: MountSpec | None = None
    alternatives: list[str] = Field(default_factory=list)
    climate_step_output: str | None = None
    envvar: str | None = None

    @model_validator(mode="after")
    def climate_step_output_required_for_climate_inputs_to_sealevel_modules(
        self,
    ) -> "InputArgSpec":
        if (
            self.name == "climate-data-file" or self.name == "input-data-file"
        ):  # TODO need to fix this
            if not self.climate_step_output:
                raise ValueError(
                    "climate_step_output is required for this type of input entry"
                )
        return self


class OutputFileSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    help: str | None = None
    filename: str | None = None
    filename_map: dict[str, Any] | None = None
    output_type: str
    optional: bool = False
    mount: MountSpec | None = None
    alternatives: list[str] = Field(default_factory=list)
    pass_to_total: bool = True


class OtherOutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    help: str | None = None
    optional: bool = False
    mount: MountSpec | None = None
    alternatives: list[str] = Field(default_factory=list)


class OutputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[OutputFileSpec] = Field(default_factory=list)
    other: list[OtherOutputSpec] = Field(default_factory=list)


class FingerprintParamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    optional: bool = False
    help: str | None = None
    filename: str | None = None
    default_value: str | None = None
    transform: str | None = None
    mount: MountSpec | None = None
    alternatives: list[str] = Field(default_factory=list)


class ArgumentsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_level: list[TopLevelArgSpec] = Field(default_factory=list)
    options: list[OptionArgSpec] = Field(default_factory=list)
    inputs: list[InputArgSpec] = Field(default_factory=list)
    outputs: OutputsSpec = Field(default_factory=OutputsSpec)
    fingerprint_params: list[FingerprintParamSpec] = Field(default_factory=list)
