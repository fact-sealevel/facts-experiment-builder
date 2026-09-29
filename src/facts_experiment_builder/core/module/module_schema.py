"""In-memory representation of a module schema (analogous to *_module.yaml).

Does not contain everything needed to run a module; used to build experiment-metadata
content and, with experiment data, to build ModuleServiceSpec.
"""

from dataclasses import dataclass, field
from typing import Any

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.module.arg_specs import (
    ArgumentsSpec,
    BaseArgSpec,
    OtherOutputSpec,
    OutputFileSpec,
)

# TODO this would need to change if the module schema yaml structure changes.
# should add an abstraction to separate these domain objects from the module schema


@dataclass(frozen=True)
class ModuleDefaultValues:
    """Default values for a module."""

    inputs: dict[str, Any]
    options: dict[str, Any]
    outputs: dict[str, Any]


@dataclass
class ModuleSchema:
    """In-memory representation of a module YAML file (*_module.yaml)."""

    module_name: str
    container_image: str
    arguments: ArgumentsSpec
    volumes: dict[str, dict[str, Any]]
    depends_on: list[dict[str, Any]] | None = None
    command: str = ""
    uses_climate_file: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    per_workflow: bool = False
    output_types: list[str] = field(default_factory=lambda: ["global", "local"])

    def __post_init__(self) -> None:
        if self.arguments is None:
            self.arguments = ArgumentsSpec()
        if self.volumes is None:
            self.volumes = {}
        if self.command is None:
            self.command = ""
        elif not isinstance(self.command, str):
            raise ValueError(
                f"Module '{self.module_name}': 'command' must be a string,"
                f"got {type(self.command).__name__}."
            )
        self.command = self.command.strip()

    @property
    def input_dir_name(self) -> str:
        return self.extra.get("input_dir_name") or self.module_name

    def get_file_outputs(self) -> list[OutputFileSpec]:
        """File outputs (have filename + output_type)."""
        return list(self.arguments.outputs.files)

    def get_other_outputs(self) -> list[OtherOutputSpec]:
        """Non-file outputs (directories, string paths, etc.)."""
        return list(self.arguments.outputs.other)

    def get_outputs_list(
        self, suppress_output_types: set | None = None
    ) -> list[OutputFileSpec | OtherOutputSpec]:
        """All outputs as a flat list (file and other combined).

        Args:
            suppress_output_types: Set of output_type values to exclude (e.g. {"local"}).
                When None or empty, all outputs are returned.
        """
        all_outputs = self.get_file_outputs() + self.get_other_outputs()
        if not suppress_output_types:
            return all_outputs
        return [
            spec
            for spec in all_outputs
            if getattr(spec, "output_type", None) not in suppress_output_types
        ]

    def output_volume_key(self) -> str | None:
        """The key in self.volumes that maps to the shared output directory, or none."""
        for vol_key, spec in self.volumes.items():
            if isinstance(spec, dict) and "output_paths" in spec.get("host_path", ""):
                return vol_key
        return None

    def get_output_volume_input_keys(self) -> set:
        """Set of input `name`s that mount from the output volume (that is not module-
        specific, is for multi-modules).

        Keyed by `name`, matching how `inputs` is keyed in the persisted experiment-
        config.yaml.
        """
        output_vol = self.output_volume_key()
        if not output_vol:
            return set()
        keys = set()
        for input_spec in self.arguments.inputs:
            if input_spec.mount is not None and input_spec.mount.volume == output_vol:
                keys.add(input_spec.name)
        return keys

    def get_climate_output_type(self) -> str | None:
        """Return the climate output name this module needs, derived from its climate
        input spec.

        Reads climate_step_output from the input entry named 'climate-data-file' or
        'input-data-file'. Returns None if this module has no such input.
        """
        for input_spec in self.arguments.inputs:
            if input_spec.name in ("climate-data-file", "input-data-file"):
                return input_spec.climate_step_output
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleSchema":
        raw_arguments = data.get("arguments") or {}
        if not isinstance(raw_arguments, dict):
            raise ValueError(
                f"Module '{data.get('module_name', '')}': 'arguments' must be a dict, "
                f"got {type(raw_arguments).__name__}."
            )
        arguments = ArgumentsSpec.model_validate(raw_arguments)

        volumes = data.get("volumes", {})
        if not isinstance(volumes, dict):
            volumes = {}
        known_keys = {
            "module_name",
            "container_image",
            "arguments",
            "volumes",
            "depends_on",
            "command",
            "uses_climate_file",
            "climate_file_required",
            "output_types",
            "per_workflow",
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}
        return cls(
            module_name=data.get("module_name", ""),
            container_image=data.get("container_image", ""),
            arguments=arguments,
            volumes=volumes,
            depends_on=data.get("depends_on"),
            command=data.get("command", ""),
            uses_climate_file=data.get("uses_climate_file", False),
            per_workflow=data.get("per_workflow") or False,
            output_types=data.get("output_types") or ["global", "local"],
            extra=extra,
        )

    def to_dict(self) -> dict:
        """Serialize back to the raw dict shape consumed by from_dict(), for freezing
        into experiment-config.yaml at setup-experiment time."""
        data: dict[str, Any] = {
            "module_name": self.module_name,
            "container_image": self.container_image,
            # exclude_unset: only write fields present in the module YAML, not every
            # model default, so the frozen schema matches the registry file.
            "arguments": self.arguments.model_dump(exclude_unset=True),
            "volumes": dict(self.volumes),
            "command": self.command,
            "uses_climate_file": self.uses_climate_file,
            "per_workflow": self.per_workflow,
            "output_types": list(self.output_types),
        }
        if self.depends_on is not None:
            data["depends_on"] = self.depends_on
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class ScenarioConfig:
    """Scenario configuration details."""

    scenario_name: str
    description: str


@dataclass(frozen=True)
class ModuleContainerImage:
    """Container image for a module."""

    image_url: str
    image_tag: str


def collect_metadata_param_keys(
    schemas: list["ModuleSchema"], section: str
) -> dict[str, str]:
    """This function loops through the ModuleSchema (rep.

    of module yaml) for each module in an ExperimentSkeleton object. It is looking for a specific section ('top-level','options','inputs',outputs', etc.)
    It pulls out the keyname (ie. 'pipeline-id' for 'metadata.pipeline-id') as well as help text, if it is included in that object's field in the module yaml file.

    Return {key_name: help_text} for args in `section` sourced from metadata.*.

    Iterates over all schemas and collects argument specs in the given section
    (e.g. "top_level" or "fingerprint_params") whose source starts with "metadata.".
    The key name is the part after "metadata." (e.g. "pipeline-id", "location-file").
    Deduplicates across schemas — first help text seen wins.

    Args:
        schemas: Loaded module schemas for the experiment.
        section: Argument section name in the module YAML ("top_level", "fingerprint_params", etc.)

    Returns:
        Dict mapping key_name to help_text.
    """
    result: dict[str, str] = {}
    for schema in schemas:
        arg_specs: list[BaseArgSpec] = getattr(schema.arguments, section)
        for arg_spec in arg_specs:
            if arg_spec.source.root == "metadata":
                # Keep the YAML spelling (e.g. "pipeline-id"): it is the config key.
                key_name = arg_spec.source.leaf
                if key_name not in result:
                    result[key_name] = (
                        arg_spec.help
                        if arg_spec.help is not None
                        else f"Enter {key_name}"
                    )
    return result
