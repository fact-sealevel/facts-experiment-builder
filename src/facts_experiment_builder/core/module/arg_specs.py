"""Pydantic models for module YAML argument spec components.

These models validate the structure of dicts inside ModuleSchema.arguments —
catching unknown fields, wrong types, and missing required keys at YAML load
time (in ModuleSchema.from_dict).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MountSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    container_path: str
    volume: str  # Optional[str] = None
    transform: Optional[str] = None


class TopLevelArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    optional: bool = False
    help: Optional[str] = None
    transform: Optional[str] = None
    mount: Optional[MountSpec] = None
    alternatives: List[str] = Field(default_factory=list)


class OptionArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    optional: bool = False
    help: Optional[str] = None
    default_value: Optional[Any] = None
    multiple: bool = False
    envvar: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    allowed_values: Optional[list] = None


class InputArgSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    help: Optional[str] = None
    filename: Optional[str] = None
    filename_map: Optional[Dict[str, Any]] = None
    default_value: Optional[Any] = None
    optional: bool = False
    multiple: bool = False
    external_volume: bool = False
    mount: Optional[MountSpec] = None
    alternatives: List[str] = Field(default_factory=list)
    climate_step_output: Optional[str] = None
    envvar: Optional[str] = None

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
    help: Optional[str] = None
    filename: Optional[str] = None
    filename_map: Optional[Dict[str, Any]] = None
    output_type: str
    optional: bool = False
    mount: Optional[MountSpec] = None
    alternatives: List[str] = Field(default_factory=list)
    pass_to_total: bool = True


class OtherOutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    help: Optional[str] = None
    optional: bool = False
    mount: Optional[MountSpec] = None
    alternatives: List[str] = Field(default_factory=list)


class OutputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: List[OutputFileSpec] = Field(default_factory=list)
    other: List[OtherOutputSpec] = Field(default_factory=list)


class FingerprintParamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    source: str
    optional: bool = False
    help: Optional[str] = None
    filename: Optional[str] = None
    default_value: Optional[str] = None
    transform: Optional[str] = None
    mount: Optional[MountSpec] = None
    alternatives: List[str] = Field(default_factory=list)


class ArgumentsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_level: List[TopLevelArgSpec] = Field(default_factory=list)
    options: List[OptionArgSpec] = Field(default_factory=list)
    inputs: List[InputArgSpec] = Field(default_factory=list)
    outputs: OutputsSpec = Field(default_factory=OutputsSpec)
    fingerprint_params: List[FingerprintParamSpec] = Field(default_factory=list)
