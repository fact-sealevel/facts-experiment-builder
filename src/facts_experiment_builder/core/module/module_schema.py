"""In-memory representation of a module schema (analogous to *_module.yaml).

Does not contain everything needed to run a module; used to build experiment-metadata
content and, with experiment data, to build ModuleServiceSpec.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec

# TODO this would need to change if the module schema yaml structure changes.
# should add an abstraction to separate these domain objects from the module schema


@dataclass(frozen=True)
class ModuleDefaultValues:
    """Default values for a module."""

    inputs: Dict[str, Any]
    options: Dict[str, Any]
    outputs: Dict[str, Any]


@dataclass
class ModuleSchema:
    """In-memory representation of a module YAML file (*_module.yaml)."""

    module_name: str
    container_image: str
    arguments: Dict[str, List[Dict[str, Any]]]  # top_level, options, inputs, outputs
    volumes: Dict[str, Dict[str, Any]]
    depends_on: Optional[List[Dict[str, Any]]] = None
    command: str = ""
    uses_climate_file: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
    per_workflow: bool = False
    output_types: List[str] = field(default_factory=lambda: ["global", "local"])

    def __post_init__(self) -> None:
        if self.arguments is None:
            self.arguments = {}
        if self.volumes is None:
            self.volumes = {}

    @property
    def input_dir_name(self) -> str:
        return self.extra.get("input_dir_name") or self.module_name

    def get_file_outputs(self) -> List[Dict[str, Any]]:
        """File outputs (have filename + output_type)."""
        outputs = self.arguments.get("outputs", {})
        if not isinstance(outputs, dict):
            raise ValueError(
                f"Module '{self.module_name}': 'arguments.outputs' must be a dict "
                f" with 'files'/'other' keys, but got {type(outputs).__name__}. "
                f" Check the module YAML for '{self.module_name}' and ensure it has correct structure."
            )
        return list(outputs.get("files") or [])

    def get_other_outputs(self) -> List[Dict[str, Any]]:
        """Non-file outputs (directories, string paths, etc.)."""
        outputs = self.arguments.get("outputs") or {}
        if not isinstance(outputs, dict):
            raise ValueError(
                f"Module '{self.module_name}': 'arguments.outputs' must be a dict "
                f" with 'files'/'other' keys, but got {type(outputs).__name__}. "
                f" Check the module YAML for '{self.module_name}' and ensure it has correct structure."
            )
        return list(outputs.get("other") or [])

    def get_outputs_list(
        self, suppress_output_types: Optional[set] = None
    ) -> List[Dict[str, Any]]:
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
            if spec.get("output_type") not in suppress_output_types
        ]

    def _output_volume_key(self) -> Optional[str]:
        """The key in self.volumes that maps tot he shared output directory, or none."""
        for vol_key, spec in self.volumes.items():
            if isinstance(spec, dict) and "output_paths" in spec.get("host_path", ""):
                return vol_key
        return None

    def get_output_volume_input_keys(self) -> set:
        """Set of input names/source-keys that mount from the output volume (that is not
        module-specific, is for mult.

        modules)         This function returns both the YAML arg name ('climate-data-
        file') and the source-derived metadata key ('climate_data_file') so the adapter
        can match either form.
        """
        output_vol = self._output_volume_key()
        if not output_vol:
            return set()
        keys = set()
        for input_spec in self.arguments.get("inputs", []):
            mount = input_spec.get("mount", {})
            if isinstance(mount, dict) and mount.get("volume") == output_vol:
                name = input_spec.get("name", "")
                if name:
                    keys.add(name)
                source = input_spec.get("source", "")
                if "." in source:
                    keys.add(source.split(".")[-1])
        return keys

    def get_climate_output_type(self) -> Optional[str]:
        """Return the climate output name this module needs, derived from its climate
        input spec.

        Reads climate_step_output from the input entry named 'climate-data-file' or
        'input-data-file'. Returns None if this module has no such input.
        """
        for input_spec in self.arguments.get("inputs", []):
            if input_spec.get("name") in ("climate-data-file", "input-data-file"):
                return input_spec.get("climate_step_output")
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleSchema":
        arguments = data.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}

        ArgumentsSpec(**arguments)
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
            per_workflow=data.get("per_workflow"),
            output_types=data.get("output_types"),
            extra=extra,
        )


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
    schemas: List["ModuleSchema"], section: str
) -> Dict[str, str]:
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
    result: Dict[str, str] = {}
    for schema in schemas:
        for arg_spec in schema.arguments.get(section, []):
            source = arg_spec.get("source", "")
            if source.startswith("metadata."):
                key_name = source[len("metadata.") :]
                if key_name not in result:
                    result[key_name] = arg_spec.get("help", f"Enter {key_name}")
    return result
