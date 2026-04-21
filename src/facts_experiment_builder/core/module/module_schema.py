"""In-memory representation of a module schema (analogous to *_module.yaml).

Does not contain everything needed to run a module; used to build
experiment-metadata content and, with experiment data, to build ModuleServiceSpec.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# TODO this would need to change if the module schema yaml structure changes.
# is that fine or do we want it to be more flexibly defined?


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

    def __post_init__(self) -> None:
        if self.arguments is None:
            self.arguments = {}
        if self.volumes is None:
            self.volumes = {}

    def get_file_outputs(self) -> List[Dict[str, Any]]:
        """File outputs (have filename + output_type)."""
        return list(self.arguments.get("outputs", {}).get("files") or [])

    def get_other_outputs(self) -> List[Dict[str, Any]]:
        """Non-file outputs (directories, string paths, etc.)."""
        return list(self.arguments.get("outputs", {}).get("other") or [])

    def get_outputs_list(self) -> List[Dict[str, Any]]:
        """All outputs as a flat list (file and other combined)."""
        return self.get_file_outputs() + self.get_other_outputs()

    def _output_volume_key(self) -> Optional[str]:
        """The key in self.volumes that maps tot he shared output directory, or none."""
        for vol_key, spec in self.volumes.items():
            if isinstance(spec, dict) and "output_paths" in spec.get("host_path", ""):
                return vol_key
        return None

    def get_output_volume_input_keys(self) -> set:
        """Set of input names/source-keys that mount from the output volume (that is not module-specific, is for mult. modules)

        This function returns both the YAML arg name ('climate-data-file') and the source-derived metadata key ('climate_data_file') so the adapter can match either form.
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

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleSchema":
        arguments = data.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
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
            extra=extra,
        )


def collect_metadata_param_keys(
    schemas: List["ModuleSchema"], section: str
) -> Dict[str, str]:
    """Return {key_name: help_text} for args in `section` sourced from metadata.*.

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
