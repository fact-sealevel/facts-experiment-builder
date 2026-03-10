"""Module in service: has all information needed to run a module and slot into an experiment implementation (e.g. one compose service)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

from facts_experiment_builder.infra.path_utils import (
    ModuleInputPaths,
    ModuleOutputPaths,
)
from facts_experiment_builder.adapters.compose_service_writer import (
    build_compose_service_dict,
)
from facts_experiment_builder.core.module.facts_module import FactsModule
from facts_experiment_builder.core.source_resolver import (
    resolve_value as resolve_source_value,
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


@dataclass(frozen=True)
class ModuleServiceSpecComponents:
    """Dataclass holding all inputs required for a ModuleServiceSpec (experiment-specific paths, values, image, metadata)."""

    module_name: str
    options: Dict[str, Any]
    input_paths: ModuleInputPaths
    output_paths: ModuleOutputPaths
    fingerprint_params: Dict[str, Any]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    image: ModuleContainerImage
    metadata: Dict[str, Any]
    output_container_base: Optional[str] = None


class ModuleServiceSpec:
    """Has all information needed to run a module and slot into an experiment implementation (e.g. one compose service).

    Built from a FactsModule (module YAML) plus experiment-specific inputs.
    """

    def __init__(
        self,
        components: ModuleServiceSpecComponents,
        module_definition: FactsModule,
    ):
        """
        Initialize ModuleServiceSpec.

        Args:
            components: Experiment-specific inputs (paths, values, image, metadata)
            module_definition: Module definition from the module YAML file (FactsModule)
        """
        self.components = components
        self.module_definition = module_definition

    # old classmethod from_yaml (was cls)
    @property
    def module_name(self) -> str:
        """Return the module name."""
        return self.components.module_name

    @property
    def image(self) -> ModuleContainerImage:
        """Return the container image."""
        return self.components.image

    @property
    def input_paths(self) -> ModuleInputPaths:
        """Return input paths (module-specific and general dirs)."""
        return self.components.input_paths

    @property
    def output_paths(self) -> ModuleOutputPaths:
        """Return output paths."""
        return self.components.output_paths

    def _resolve_value(self, source: str) -> Any:
        """Resolve a value from a source path using the shared SourceResolver."""
        context = {
            "metadata": self.components.metadata,
            "module_inputs": self.components,
        }
        return resolve_source_value(source, context)

    def _build_command_args(self) -> List[str]:
        """
        Build command arguments from YAML configuration.

        Returns:
            List of command-line arguments (with command name first if specified)
        """
        command_args = []

        # Check if a specific command is specified (e.g., "glaciers" or "icesheets")
        command = self.module_definition.command or ""
        if command:
            command_args.append(command)  # Add command name first

        arguments_config = self.module_definition.arguments

        # Process top-level arguments
        for arg_spec in arguments_config.get("top_level", []):
            value = self._process_argument(arg_spec)
            if value is not None:
                command_args.append(f"--{arg_spec['name']}={value}")

        if "facts-total" not in self.module_name:
            # Process fingerprint params
            for arg_spec in arguments_config.get("fingerprint_params", []):
                value = self._process_argument(arg_spec)
                if value is not None:
                    command_args.append(f"--{arg_spec['name']}={value}")
        # Process options
        for arg_spec in arguments_config.get("options", []):
            value = self._process_argument(arg_spec)
            if value is not None:
                command_args.append(f"--{arg_spec['name']}={value}")

        # Process inputs
        for arg_spec in arguments_config.get("inputs", []):
            value = self._process_argument(arg_spec)
            if value is not None:
                # Handle multiple inputs (e.g., --item can be specified multiple times)
                if arg_spec.get("multiple", False):
                    if isinstance(value, list):
                        for v in value:
                            command_args.append(f"--{arg_spec['name']}={v}")
                    else:
                        command_args.append(f"--{arg_spec['name']}={value}")
                else:
                    command_args.append(f"--{arg_spec['name']}={value}")

        # Process outputs
        for arg_spec in arguments_config.get("outputs", []):
            value = self._process_output_argument(arg_spec)
            if value is not None:
                command_args.append(f"--{arg_spec['name']}={value}")

        return command_args

    def _process_argument(self, arg_spec: Dict[str, Any]) -> Any:
        """
        Process a single argument specification.

        Args:
            arg_spec: Argument specification from YAML

        Returns:
            Processed value or None if optional and not present
        """
        source = arg_spec.get("source", "")
        if not source:
            return None

        # Resolve the value
        value = self._resolve_value(source)
        # Handle optional arguments
        if value is None and arg_spec.get("optional", False):
            return None

        if value is None:
            # Try to get from alternative source paths
            alt_sources = arg_spec.get("alternatives", [])
            for alt_source in alt_sources:
                value = self._resolve_value(alt_source)
                if value is not None:
                    break

        if value is None:
            return None

        # Apply transform if specified
        transform = arg_spec.get("transform")
        mount = arg_spec.get("mount", {})
        if transform == "scenario_name":
            if hasattr(value, "scenario_name"):
                value = value.scenario_name
            elif isinstance(value, dict):
                value = value.get("scenario_name", value.get("scenario", value))
        elif transform == "filename":
            # Skip for output-volume args that are paths under output root (e.g. fair-temperature/climate.nc).
            if isinstance(value, (str, Path)) and not (
                mount.get("volume") == "output" and "/" in str(value)
            ):
                value = Path(value).name

        # Handle mount transformations for file paths (inputs and options only; outputs use _process_output_argument).
        if mount and isinstance(value, (str, Path)):
            container_path = (mount.get("container_path") or "").rstrip("/")
            if (
                container_path
                and mount.get("volume") == "output"
                and "/" in str(value)
                and not Path(value).is_absolute()
            ):
                # Path under output root from another service (e.g. fair-temperature/climate.nc) -> /mnt/out/fair-temperature/climate.nc
                return f"{container_path}/{value}"
            if container_path:
                # Transform to container path
                if transform == "filename":
                    value = f"{container_path}/{Path(value).name}"
                else:
                    # Preserve relative path structure from input_dir
                    # Compute relative path from module input directory to preserve subdirectory structure
                    value_path = Path(value)
                    if value_path.is_absolute() and hasattr(
                        self.components, "input_paths"
                    ):
                        input_dir = Path(self.components.input_paths.input_dir)
                        try:
                            # Compute relative path from input_dir to the file
                            relative_path = value_path.relative_to(input_dir)
                            value = str(Path(container_path) / relative_path)
                        except ValueError:
                            # If paths don't share a common base, fall back to filename only
                            value = str(Path(container_path) / value_path.name)
                    else:
                        # Relative: preserve path (e.g. rcmip/file.csv -> container/rcmip/file.csv).
                        # Absolute: Path(container_path)/value_path would return value_path (absolute wins), leaking host path; use filename only.
                        value = str(
                            Path(container_path) / value_path.parent / value_path.name
                            if not value_path.is_absolute()
                            else Path(container_path) / value_path.name
                        )

        return value

    def _process_output_argument(self, arg_spec: Dict[str, Any]) -> Any:
        """
        Process a single output argument: resolve value from module_inputs.outputs.*
        and build container path as <container_path>/<module_name>/<filename>.

        Returns:
            Container path string (e.g. /mnt/out/fair-temperature/gsat.nc) or None.
        """
        source = arg_spec.get("source", "")
        if not source:
            return None

        value = self._resolve_value(source)
        if value is None and arg_spec.get("optional", False):
            return None
        if value is None:
            for alt_source in arg_spec.get("alternatives", []):
                value = self._resolve_value(alt_source)
                if value is not None:
                    break
        if value is None:
            return None

        mount = arg_spec.get("mount", {})
        if not mount or not isinstance(value, (str, Path)):
            return value

        container_path = (mount.get("container_path") or "").rstrip("/")
        volume = mount.get("volume", "")
        filename = Path(value).name
        if volume == "output" and container_path:
            output_container_base = (
                getattr(self.components, "output_container_base", None) or None
            )
            if output_container_base:
                base = (output_container_base or "").rstrip("/")
                return f"{base}/{filename}"
            base = f"{container_path}/{self.components.module_name}"
            # If value is already a path ending in module_name (e.g. output-dir), avoid duplicating it
            if filename == self.components.module_name:
                return base
            return f"{base}/{filename}"
        return value

    def _build_volumes(self) -> List[str]:
        """
        Build volumes list from YAML configuration.

        Returns:
            List of volume mount strings in format "host_path:container_path"
        """
        volumes = []
        volumes_config = self.module_definition.volumes

        for volume_name, volume_spec in volumes_config.items():
            if not isinstance(volume_spec, dict):
                continue

            host_path_source = volume_spec.get("host_path", "")
            # Skip optional external volumes (no runtime path is provided)
            if volume_spec.get("optional", False) and "external." in host_path_source:
                continue
            if host_path_source.startswith("external."):
                continue  # External volumes are not supported; skip

            # Resolve host path from module_inputs
            host_path = self._resolve_value(host_path_source)
            if host_path is None:
                continue
            host_path = str(Path(host_path).resolve())
            # For the output volume: mount the shared output root (parent of per-module dir)
            # so source is .../output and dest is /mnt/out; container paths use /mnt/out/<module_name>/...
            if volume_name == "output":
                host_path = str(Path(host_path).parent)

            container_path = volume_spec.get("container_path", "")
            if host_path and container_path:
                volumes.append(f"{host_path}:{container_path}")

        return volumes

    def _build_depends_on(
        self, temperature_service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build depends_on dictionary from YAML configuration.

        If uses_climate_file is True, automatically adds dependency on temperature service.
        Also processes any explicit depends_on entries from YAML (for backward compatibility).

        Args:
            temperature_service_name: Optional name of the temperature service to map "fair" to

        Returns:
            Dictionary mapping service names to dependency conditions
        """
        depends_on = {}

        # Check if this module uses climate files - if so, add dependency on temperature service
        uses_climate_file = self.module_definition.uses_climate_file
        if uses_climate_file and temperature_service_name:
            depends_on[temperature_service_name] = {
                "condition": "service_completed_successfully"
            }

        # Also process explicit depends_on entries from YAML (for backward compatibility)
        depends_on_config = self.module_definition.depends_on or []

        if depends_on_config:
            for dep_spec in depends_on_config:
                if isinstance(dep_spec, dict):
                    service_name = dep_spec.get("service", "")
                    condition = dep_spec.get(
                        "condition", "service_completed_successfully"
                    )
                    if service_name:
                        # Map "fair" to the actual temperature service name if provided
                        if service_name == "fair" and temperature_service_name:
                            service_name = temperature_service_name
                        depends_on[service_name] = {"condition": condition}
                elif isinstance(dep_spec, str):
                    # Simple string format
                    mapped_name = dep_spec
                    if dep_spec == "fair" and temperature_service_name:
                        mapped_name = temperature_service_name
                    depends_on[mapped_name] = {
                        "condition": "service_completed_successfully"
                    }

        return depends_on

    def generate_compose_service(
        self, temperature_service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate Docker Compose service configuration.

        Args:
            temperature_service_name: Optional name of the temperature service (e.g., "fair-temperature") to map "fair" dependencies to

        Returns:
            Dictionary representing a Docker Compose service
        """
        image_str = (
            f"{self.components.image.image_url}:{self.components.image.image_tag}"
        )
        command = self._build_command_args()
        volumes = self._build_volumes()
        depends_on = self._build_depends_on(
            temperature_service_name=temperature_service_name
        )
        return build_compose_service_dict(
            image_str=image_str,
            command=command,
            volumes=volumes,
            depends_on=depends_on,
        )

    def generate_asyncflow_config(self) -> Dict[str, Any]:
        """
        Generate AsyncFlow configuration.

        Returns:
            Dictionary representing AsyncFlow configuration
        """
        raise NotImplementedError(
            "AsyncFlow configuration generation is not implemented"
        )
        # TODO: Implement AsyncFlow configuration generation
        # This is a placeholder for future implementation
        # return {
        #    'module_name': self.module_name,
        #     'image': f"{self.image.image_url}:{self.image.image_tag}",
        # }
