"""Module in service: has all information needed to run a module and slot into an
experiment implementation (e.g. one compose service)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import os

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.typed_path import (
    TypedPath,
    PathValue,
    ContainerPath,
    HostDirPath,
    HostPath,
    ExperimentSpecificInputPath,
)
from facts_experiment_builder.core.module.service_spec_utils import (
    _dir_input_keys,
    _input_spec_by_key,
    _multiple_file_input_keys,
    expand_path,
    resolve_input_path,
    resolve_output_path,
    get_required_field,
    get_experiment_paths,
)
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
    build_module_input_paths,
    build_module_output_paths,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
    ModuleContainerImage,
)
from facts_experiment_builder.core.source_resolver import (
    resolve_value as resolve_source_value,
)
from facts_experiment_builder.core.transforms import scenario_name_ssp_landwaterstorage

# ---------------------- IO imports ----------------------------
from facts_experiment_builder.io.compose_service_writer import (
    build_compose_service_dict,
)


@dataclass(frozen=True)
class ModuleServiceSpecComponents:
    """Dataclass holding all inputs required for a ModuleServiceSpec (experiment-
    specific paths, values, image, metadata)."""

    module_name: str
    options: Dict[str, Any]
    input_paths: ModuleInputPaths
    output_paths: ModuleOutputPaths
    fingerprint_params: Dict[str, Any]
    inputs: Dict[str, Union[PathValue, Any]]
    outputs: Dict[str, Any]
    image: ModuleContainerImage
    metadata: Dict[str, Any]
    output_container_base: Optional[str] = None


class ModuleServiceSpec:
    """Has all information needed to run a module and slot into an experiment
    implementation (e.g. one compose service).

    Built from a ModuleSchema (module YAML) plus experiment-specific inputs.
    """

    def __init__(
        self,
        components: ModuleServiceSpecComponents,
        module_definition: ModuleSchema,
    ):
        """Initialize ModuleServiceSpec.

        Args:
            components: Experiment-specific inputs (paths, values, image, metadata)
            module_definition: Module definition from the module YAML file (ModuleSchema)
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

    def _build_command_args(
        self, suppress_output_types: Optional[set] = None
    ) -> List[str]:
        """Build command arguments from YAML configuration.

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

        if not self.module_definition.extra.get("skip_fingerprint_params"):
            # Process fingerprint params
            for arg_spec in arguments_config.get("fingerprint_params", []):
                value = self._process_argument(arg_spec)
                if value is not None:
                    command_args.append(f"--{arg_spec['name']}={value}")
        # Process options
        for arg_spec in arguments_config.get("options", []):
            value = self._process_argument(arg_spec)
            if value is not None:
                if isinstance(value, list):
                    for v in value:
                        command_args.append(f"--{arg_spec['name']}={v}")
                else:
                    command_args.append(f"--{arg_spec['name']}={value}")

        # Process inputs (skip args that are handled via environment variable)
        for arg_spec in arguments_config.get("inputs", []):
            if arg_spec.get("envvar"):
                continue
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
        for arg_spec in self.module_definition.get_outputs_list(
            suppress_output_types=suppress_output_types
        ):
            value = self._process_output_argument(arg_spec)
            if value is not None:
                command_args.append(f"--{arg_spec['name']}={value}")

        return command_args

    def _host_path_to_container(self, path_str: str, arg_spec: Dict[str, Any]) -> str:
        """Transform a host path to container path using mount and transform from
        arg_spec."""
        mount = arg_spec.get("mount", {})
        transform = arg_spec.get("transform")
        container_path = (mount.get("container_path") or "").rstrip("/")
        if not container_path:
            return path_str
        value_path = Path(path_str)
        if transform == "filename":
            return f"{container_path}/{value_path.name}"
        if value_path.is_absolute() and hasattr(self.components, "input_paths"):
            input_dir = Path(self.components.input_paths.input_dir)
            try:
                relative_path = value_path.relative_to(input_dir)
                return str(Path(container_path) / relative_path)
            except ValueError:
                return str(Path(container_path) / value_path.name)
        return str(
            Path(container_path) / value_path.name
            if value_path.is_absolute()
            else Path(container_path) / value_path.parent / value_path.name
        )

    def _process_argument(
        self,
        arg_spec: Dict[str, Any],
    ) -> Any:
        """Process a single argument specification.

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
        elif transform == "scenario_name_ssp_landwaterstorage":
            mapping = self.module_definition.extra.get("scenario_name_mapping", {})
            value = scenario_name_ssp_landwaterstorage(value, mapping=mapping)
        elif transform == "filename":
            # Skip for output-volume args that are paths under output root (e.g. fair-temperature/climate.nc).
            if isinstance(value, (str, Path)) and not (
                mount.get("volume") == "output" and "/" in str(value)
            ):
                value = Path(value).name

        # Typed paths: routing by kind.
        if mount and isinstance(value, TypedPath):
            if value.kind == "container":
                return value.path
            if value.kind == "experiment_specific_in":
                return f"/mnt/experiment_specific_in/{Path(value.path).name}"
            result = self._host_path_to_container(value.path, arg_spec)
            if value.kind == "host_dir":
                return result.rstrip("/") + "/"
            return result
        if mount and isinstance(value, list) and len(value) > 0:
            if all(isinstance(v, TypedPath) for v in value):
                if value[0].kind == "container":
                    return [tp.path for tp in value]
                return [self._host_path_to_container(tp.path, arg_spec) for tp in value]
            pass

        # Handle mount transformations for file paths (legacy str/Path; outputs use _process_output_argument).
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
        """Process a single output argument: resolve value from module_inputs.outputs.*
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
        """Build volumes list from YAML configuration.

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

        for inp_value in self.components.inputs.values():
            if (
                isinstance(inp_value, TypedPath)
                and inp_value.kind == "experiment_specific_in"
            ):
                host_dir = str(Path(inp_value.path).parent.resolve())
                volumes.append(f"{host_dir}:/mnt/experiment_specific_in")
                break

        return volumes

    def _build_depends_on(
        self, temperature_service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build depends_on dictionary from YAML configuration.

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

    def _build_environment(self) -> Dict[str, str]:
        """Build environment variable dict for args declared with envvar in the module
        YAML.

        For each input arg that has an `envvar` key, the resolved container-path value
        (if any) is added to the environment dict under the declared variable name. Args
        with no resolvable value are omitted — the container's own defaults or host
        environment handle them.
        """
        environment: Dict[str, str] = {}
        for arg_spec in self.module_definition.arguments.get("inputs", []):
            envvar = arg_spec.get("envvar")
            if not envvar:
                continue
            value = self._process_argument(arg_spec)
            if value is not None:
                environment[envvar] = str(value)
        return environment

    def generate_compose_service(
        self,
        temperature_service_name: Optional[str] = None,
        suppress_output_types: Optional[set] = None,
    ) -> Dict[str, Any]:
        """Generate Docker Compose service configuration.

        Args:
            temperature_service_name: Optional name of the temperature service (e.g., "fair-temperature") to map "fair" dependencies to

        Returns:
            Dictionary representing a Docker Compose service
        """
        image_str = (
            f"{self.components.image.image_url}:{self.components.image.image_tag}"
        )
        command = self._build_command_args(suppress_output_types=suppress_output_types)
        volumes = self._build_volumes()
        depends_on = self._build_depends_on(
            temperature_service_name=temperature_service_name
        )
        environment = self._build_environment()
        return build_compose_service_dict(
            image_str=image_str,
            command=command,
            volumes=volumes,
            depends_on=depends_on,
            environment=environment,
        )

    def generate_asyncflow_config(self) -> Dict[str, Any]:
        """Generate AsyncFlow configuration.

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


@dataclass
class _ResolvedPaths:
    shared_input_data: str
    module_specific_input_data: str
    experiment_specific_input_data: Optional[str]
    output_data_location: str
    output_container_base: Optional[str] = None


@dataclass
class ExperimentOutputPath:
    path: str


def _resolve_experiment_paths(
    metadata: Dict[str, Any],
    module_context: str,
    known_module_names: list,
    module_name: str,
    module_definition: ModuleSchema,
) -> _ResolvedPaths: #tuple[ModuleInputPaths, ModuleOutputPaths, Union[str, Path]]:
    # module_name = module_definition.module_name
    experiment_paths = get_experiment_paths(metadata, module_context)
    module_metadata = get_required_field(metadata, module_name, module_context)

    raw_exp_specific = metadata.get("experiment-specific-input-data")
    if isinstance(raw_exp_specific, dict):
        raw_exp_specific = raw_exp_specific.get("value")
    experiment_specific_input = (
        expand_path(
            raw_exp_specific, f"{module_context} (experiment-specific-input-data)"
        )
        if raw_exp_specific
        else None
    )

    shared_input_data = expand_path(
        experiment_paths["shared_input_data"],
        f"{module_context} (shared-input-data)",
    )

    module_specific_input_base = expand_path(
        experiment_paths["module_specific_input_data"],
        f"{module_context} (module-specific-input-data)",
    )
    # If metadata points at a specific module's dir (e.g. .../fair-temperature), use parent as base
    # so volume host path is always base + current module's suffix only (never another module's name).
    if (
        Path(module_specific_input_base).name in known_module_names
    ):  # registry.module_names():
        module_specific_input_base = str(Path(module_specific_input_base).parent)
    # Module-specific input dir: driven by input_dir_name in module YAML (e.g. "ipccar5" for both
    # ipccar5-glaciers and ipccar5-icesheets). Falls back to module_definition.module_name so that
    # per-workflow service names (e.g. extremesealevel-pointsoverthreshold-wf1) resolve to the base
    # module's dir automatically.
    module_specific_input_path_suffix = module_definition.input_dir_name  # ()
    module_specific_input_data = (
        module_specific_input_base + "/" + module_specific_input_path_suffix
    )

    output_data_partial = expand_path(
        experiment_paths["output_data_location"],
        f"{module_context} (output-data-location)",
    )
    # Only facts-total workflow services (names like facts-total-wf1) use a shared output
    # subdir and optional container base. Other modules are unchanged.
    is_facts_total_workflow = module_name.startswith("facts-total-")
    if is_facts_total_workflow:
        output_data_location = output_data_partial + "/facts-total"
        if not Path(output_data_location).exists():
            os.makedirs(output_data_location, exist_ok=True)

        output_container_base = (
            module_metadata.get("_output_container_base")
            or "/mnt/total_out/facts-total"
        )
    else:
        output_data_location = output_data_partial + "/" + module_name
        if not Path(output_data_location).exists():
            os.makedirs(output_data_location, exist_ok=True)
        output_container_base = None

    resolved_paths = _ResolvedPaths(
        shared_input_data=shared_input_data,
        module_specific_input_data=module_specific_input_data,
        output_data_location=output_data_location,
        experiment_specific_input_data=experiment_specific_input,
        output_container_base=output_container_base,
    )
    return resolved_paths


def _resolve_module_inputs_dict(
    module_definition: ModuleSchema,
    module_context: str,
    module_inputs_section: dict,
    shared_input_data: str,
    module_specific_input_data: str,
    experiment_specific_input_data: Optional[str],
    module_name: str,
):
    # Inputs that mount from the shared output volume produced by another serivce (such as fair-temperature)
    # They're stored as relative paths (ie. fair-temperature/climate.nc -> /mnt/out/fair-temperature/climate.nc)
    # Prev. this was a hard-coded list of the names used for climate-data-file across different module yamls...
    output_root_relative_inputs = module_definition.get_output_volume_input_keys()
    input_spec = _input_spec_by_key(module_definition)
    multiple_file_input_keys = _multiple_file_input_keys(module_definition)
    dir_input_keys = _dir_input_keys(module_definition)
    # module_name = module_definition.module_name

    inputs_dict = {}
    for key, value in module_inputs_section.items():
        if key == "input_dir":
            continue
        if key in multiple_file_input_keys:
            # List of already container paths (e.g. facts-total item from generate_compose): do not resolve.
            if (
                isinstance(value, list)
                and value
                and all(str(v).strip().startswith("/mnt/") for v in value if v)
            ):
                inputs_dict[key] = [ContainerPath(str(v).strip()) for v in value if v]
                continue
            # Multiple file inputs with host paths (e.g. gwd_file): resolve each path, wrap as HostPath
            if isinstance(value, list):
                items = [v for v in value if v is not None and str(v).strip()]
            else:
                actual = value.get("value", value) if isinstance(value, dict) else value
                if isinstance(actual, list):
                    items = [v for v in actual if v is not None and str(v).strip()]
                else:
                    items = (
                        [actual] if actual is not None and str(actual).strip() else []
                    )
            resolved = []
            for item in items:
                item_value = item if isinstance(item, (str, dict)) else {"value": item}
                try:
                    resolved.append(
                        resolve_input_path(
                            field_name=key,
                            field_value=item_value,
                            mount=input_spec.get(key, {}).get("mount"),
                            shared_input_data=shared_input_data,
                            module_specific_input_data=module_specific_input_data,
                            module_name=module_name,
                            context=module_context,
                        )
                    )
                except (ValueError, KeyError, TypeError) as e:
                    error_msg = str(e)
                    if "None" in error_msg or "NoneType" in error_msg:
                        raise ValueError(
                            f"Input field '{key}' in {module_context} has None value or None in path resolution. "
                            f"Original error: {error_msg}. "
                            f"Check that '{key}' has a valid value in metadata.{module_name}.inputs"
                        ) from e
                    resolved.append(
                        item_value.get("value", item_value)
                        if isinstance(item_value, dict)
                        else item_value
                    )
            inputs_dict[key] = [HostPath(p) for p in resolved]
            continue
        if isinstance(value, list):
            # e.g. facts-total inputs.item: list of container paths (/mnt/total_out/...)
            inputs_dict[key] = [ContainerPath(str(v).strip()) for v in value if v]
            continue
        if isinstance(value, str) or (isinstance(value, dict) and "value" in value):
            actual = (
                value.get("value", value) if isinstance(value, dict) else value
            ) or ""
            if (
                key in output_root_relative_inputs
                and isinstance(actual, str)
                and actual.strip()
                and not actual.strip().startswith("/")
                and ".." not in actual
            ):
                inputs_dict[key] = actual.strip()  # e.g. "fair-temperature/climate.nc"
                continue
            if (
                key in output_root_relative_inputs
                and isinstance(actual, str)
                and actual.strip().startswith("/")
                and experiment_specific_input_data
            ):
                inputs_dict[key] = ExperimentSpecificInputPath(actual.strip())
                continue
            try:
                resolved_path = resolve_input_path(
                    field_name=key,
                    field_value=value,
                    mount=input_spec.get(key, {}).get("mount"),
                    shared_input_data=shared_input_data,
                    module_specific_input_data=module_specific_input_data,
                    module_name=module_name,
                    context=module_context,
                )
                inputs_dict[key] = (
                    HostDirPath(resolved_path)
                    if key in dir_input_keys
                    else HostPath(resolved_path)
                )
            except (ValueError, KeyError, TypeError) as e:
                error_msg = str(e)
                if "None" in error_msg or "NoneType" in error_msg:
                    raise ValueError(
                        f"Input field '{key}' in {module_context} has None value or None in path resolution. "
                        f"Original error: {error_msg}. "
                        f"Check that '{key}' has a valid value in metadata.{module_name}.inputs"
                    ) from e
                if isinstance(value, dict):
                    inputs_dict[key] = value.get("value", value)
                else:
                    inputs_dict[key] = value
        else:
            inputs_dict[key] = value

    return inputs_dict


def _resolve_module_outputs_dict(
    module_definition: ModuleSchema,
    module_outputs: Union[dict, list],
    module_context: str,
    module_name: str,
    output_data_location,
) -> dict:
    outputs_dict = {}
    outputs_config = module_definition.get_outputs_list()

    if isinstance(module_outputs, dict):
        for output_spec in outputs_config:
            output_name = output_spec.get("name", "")
            source = output_spec.get("source", "")
            key = source.split(".")[-1] if "." in source else output_name
            if not output_name or output_name not in module_outputs:
                raise KeyError(
                    f"Output '{output_name}' not found in metadata for {module_context}. "
                    f"Expected one of: {list(module_outputs.keys())}"
                )
            output_value = module_outputs[output_name]
            try:
                resolved_path = resolve_output_path(
                    output_value, output_data_location, module_context
                )
                outputs_dict[key] = resolved_path
            except ValueError:
                outputs_dict[key] = output_value
    elif isinstance(module_outputs, list):
        raise ValueError("Expected module_outputs to be dict, instead received list.")

    else:
        raise ValueError(
            f"{module_name}.outputs must be a list or dictionary in {module_context}"
        )
    return outputs_dict


def _parse_image(image_data, module_context) -> ModuleContainerImage:
    if isinstance(image_data, str):
        if ":" in image_data:
            image_url, image_tag = image_data.rsplit(":", 1)
        else:
            raise ValueError(
                f"Expected ':' in image url to reference version tag. Received '{image_data}"
            )

    else:
        raise ValueError(
            f"invalid image format in {module_context}, received: {image_data}."
            f"Expected image_data to be a string, received: {type(image_data)}"
        )
    image = ModuleContainerImage(image_url=image_url, image_tag=image_tag)
    return image


def _assemble_fingerprint_params(module_fp_section, location_file):
    fingerprint_params = {"location_file": location_file}

    if isinstance(module_fp_section, dict):
        for k, v in module_fp_section.items():
            actual = v.get("value", v) if isinstance(v, dict) else v
            if actual is not None:
                fingerprint_params[k.replace("-", "_")] = actual
    return fingerprint_params


def build_module_service_spec(
    metadata: Dict[str, Any],
    # experiment_dir: Path,
    module_name: str,
    known_module_names: List,
    module_definition: ModuleSchema,
) -> ModuleServiceSpec:
    """Build a ModuleServiceSpec for the given module from experiment metadata and
    module YAML.

    Args:
        metadata: Experiment metadata dictionary
        experiment_dir: Path to experiment directory
        module_name: Module name (e.g. 'fair-temperature', 'bamber19-icesheets')

    Returns:
        ModuleServiceSpec instance
    """
    module_context = f"{module_name} module"

    module_metadata = get_required_field(metadata, module_name, module_context)

    # scenario_name = get_required_field(metadata, "scenario", module_context)

    resolved_paths = _resolve_experiment_paths(
        metadata=metadata,
        module_context=module_context,
        known_module_names=known_module_names,
        module_name=module_name,
        module_definition=module_definition,
    )
    input_paths = build_module_input_paths(
        module_specific_input_dir=resolved_paths.module_specific_input_data,
        shared_input_dir=resolved_paths.shared_input_data,
        module_name=module_name,
    )
    output_type = module_metadata.get("output_type", "")
    output_paths = build_module_output_paths(
        output_dir=resolved_paths.output_data_location, 
        module_name=module_name, 
        output_type=output_type
    )

    module_inputs_section = get_required_field(
        module_metadata, "inputs", module_context
    )

    options_dict = {}
    options_section = module_metadata.get("options", {})
    if isinstance(options_section, dict):
        for key, value in options_section.items():
            if not key.startswith("#"):
                options_dict[key] = value

    inputs_dict = _resolve_module_inputs_dict(
        module_definition=module_definition,
        module_context=module_context,
        module_name=module_name,
        module_inputs_section=module_inputs_section,
        shared_input_data=resolved_paths.shared_input_data,
        module_specific_input_data=resolved_paths.module_specific_input_data,
        experiment_specific_input_data=resolved_paths.experiment_specific_input_data,
    )
    for opt_spec in module_definition.arguments.get("options", []):
        source = opt_spec.get("source", "")
        if "module_inputs.inputs." in source and "." in source:
            field = source.split(".")[-1]
            if field not in inputs_dict and field in options_dict:
                inputs_dict[field] = options_dict[field]
    for opt_spec in module_definition.arguments.get("options", []):
        name = opt_spec.get("name", "")
        if name and name not in options_dict and name in inputs_dict:
            options_dict[name] = inputs_dict[name]

    module_outputs = get_required_field(module_metadata, "outputs", module_context)

    outputs_dict = _resolve_module_outputs_dict(
        module_definition=module_definition,
        module_outputs=module_outputs,
        module_context=module_context,
        module_name=module_name,
        output_data_location=resolved_paths.output_data_location,
    )

    image_data = get_required_field(module_metadata, "image", module_context)
    image = _parse_image(image_data, module_context)

    location_file = metadata.get("location-file")
    # Merge module-specific fingerprint params (e.g. fprint_gis_file for emulandice-gris)
    module_fp_section = module_metadata.get("fingerprint_params") or {}
    fingerprint_params = _assemble_fingerprint_params(
        module_fp_section=module_fp_section, location_file=location_file
    )

    impl_inputs = ModuleServiceSpecComponents(
        module_name=module_name,
        options=options_dict,
        input_paths=input_paths,
        output_paths=output_paths,
        fingerprint_params=fingerprint_params,
        inputs=inputs_dict,
        outputs=outputs_dict,
        image=image,
        metadata=metadata,
        output_container_base=resolved_paths.output_container_base,
    )

    return ModuleServiceSpec(
        components=impl_inputs,
        module_definition=module_definition,
    )
