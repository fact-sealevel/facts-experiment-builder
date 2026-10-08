"""Module in service: has all information needed to run a module and slot into an
experiment implementation (e.g. one compose service)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.module.arg_specs import (
    BaseArgSpec,
    OtherOutputSpec,
    OutputFileSpec,
)
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleContainerImage,
    ModuleSchema,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    resolve_input_path,
    resolve_output_path,
)

from facts_experiment_builder.core.module.source_path import SourcePath

from facts_experiment_builder.core.typed_path import (
    ContainerPath,
    ExperimentSpecificInputPath,
    HostDirPath,
    HostPath,
    PathValue,
    TypedPath,
)


def _transform_of(arg_spec: BaseArgSpec) -> str | None:
    """Return an arg spec's `transform`, or None if its spec type has no such field.

    `transform` is only declared on TopLevelArgSpec and FingerprintParamSpec, but
    `_to_input_container_path()` and `_host_path_to_container()` handle specs from every
    section (typed as BaseArgSpec), so `arg_spec.transform` would raise AttributeError
    for option and input specs. Adding `transform` to BaseArgSpec instead would make
    module YAMLs that set it on options/inputs pass validation, which `extra="forbid"`
    currently rejects.
    """
    return getattr(arg_spec, "transform", None)


def _format_arg(name: str, value: Any) -> list[str]:
    """Format one argument as CLI flags; a list becomes one flag per item (ie.

    a click arg w/ multiple=True)
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [f"--{name}={v}" for v in value]
    return [f"--{name}={value}"]


@dataclass(frozen=True)
class ModuleServiceSpecComponents:
    """Dataclass holding all inputs required for a ModuleServiceSpec (experiment-
    specific paths, values, image, top-level params).

    Module YAML `source:` strings address these fields: `metadata.<param>` reads
    `top_level_params`, and `module_inputs.<attr>[.<key>]` reads the other fields.
    """

    module_name: str
    options: dict[str, Any]
    input_paths: ModuleInputPaths
    output_paths: ModuleOutputPaths
    fingerprint_params: dict[str, Any]
    inputs: dict[str, PathValue | Any]
    outputs: dict[str, Any]
    image: ModuleContainerImage
    top_level_params: TopLevelParams
    output_container_base: str | None = None

    def resolve(self, source: SourcePath) -> Any:
        """Return the value a module YAML source path points at.

        Returns None when the addressed key is absent (e.g. an optional input that was
        not provided), so the argument is left off the command.
        """
        if source.root == "metadata":
            return getattr(self.top_level_params, source.attr)
        value = getattr(self, source.attr)
        if source.key is None:
            return value
        if isinstance(value, dict):
            if source.key in value:
                return value[source.key]
            # TODO: confirm whether any of these dicts is keyed by the snake_case
            # form of a kebab-case source key; if not, this fallback can go.
            return value.get(source.key.replace("-", "_"))
        return getattr(value, source.key.replace("-", "_"), None)


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

    def _resolve_value(self, source: SourcePath) -> Any:
        """Resolve a module YAML source path against this module's components."""
        return self.components.resolve(source)

    def _build_command_args(
        self, suppress_output_types: set | None = None
    ) -> list[str]:
        """Build command arguments from YAML configuration.

        Returns:
            List of command-line arguments (with command name first if specified)
        """
        command_args = []

        # Check if a specific command is specified (e.g., "glaciers" or "icesheets")
        if self.module_definition.command:
            command_args.append(
                self.module_definition.command
            )  # Add command name first

        arguments_config = self.module_definition.arguments

        # Process top-level arguments
        for arg_spec in arguments_config.top_level:
            command_args.extend(
                _format_arg(arg_spec.name, self._process_argument(arg_spec))
            )

        if not self.module_definition.extra.get("skip_fingerprint_params"):
            # Process fingerprint params
            for arg_spec in arguments_config.fingerprint_params:
                command_args.extend(
                    _format_arg(arg_spec.name, self._process_argument(arg_spec))
                )
        # Process options
        for arg_spec in arguments_config.options:
            command_args.extend(
                _format_arg(arg_spec.name, self._process_argument(arg_spec))
            )

        # Process inputs (skip args that are handled via environment variable)
        for arg_spec in arguments_config.inputs:
            if arg_spec.envvar:
                continue
            # value = self._process_argument(arg_spec)
            command_args.extend(
                _format_arg(arg_spec.name, self._process_argument(arg_spec))
            )

        # Process outputs
        for arg_spec in self.module_definition.get_outputs_list(
            suppress_output_types=suppress_output_types
        ):
            command_args.extend(
                _format_arg(arg_spec.name, self._process_argument(arg_spec))
            )

        return command_args

    def _host_path_to_container(self, path_str: str, arg_spec: BaseArgSpec) -> str:
        """Transform a host path to container path using mount and transform from
        arg_spec."""
        mount = arg_spec.mount
        transform = _transform_of(arg_spec)
        container_path = (mount.container_path if mount else "").rstrip("/")
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
        arg_spec: BaseArgSpec,
    ) -> Any:
        """Resolve an argument's value and map it to its container form.

        Output specs (OutputFileSpec, OtherOutputSpec) are routed to
        `_to_output_container_path`; all other specs (top-level, fingerprint params,
        options, inputs) to `_to_input_container_path`.

        Args:
            arg_spec: Argument specification from the module YAML

        Returns:
            The value to pass to the container, or None if no value resolved
        """
        value = self._resolve_value(arg_spec.source)
        if value is None:
            return None

        if isinstance(arg_spec, (OutputFileSpec, OtherOutputSpec)):
            return self._to_output_container_path(value, arg_spec)
        return self._to_input_container_path(value, arg_spec)

    def _to_output_container_path(
        self,
        value: Any,
        arg_spec: BaseArgSpec,
    ) -> Any:
        """Map a resolved output value to its container path.

        For outputs on the shared output volume the path is
        <container_path>/<module_name>/<filename>, or <output_container_base>/<filename>
        when output_container_base is set (facts-total workflow services).

        Args:
            value: Resolved output value (host path or filename)
            arg_spec: Output argument specification from the module YAML

        Returns:
            Container path string (e.g. /mnt/out/fair-temperature/gsat.nc), or the
            value unchanged if it has no mount, is not a path, or is on another volume.
        """
        mount = arg_spec.mount
        if not mount or not isinstance(value, (str, Path)):
            return value

        container_path = mount.container_path.rstrip("/")
        volume = mount.volume
        filename = Path(value).name
        if volume == self.module_definition.output_volume_key() and container_path:
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

    def _to_input_container_path(self, value, arg_spec):
        """Apply transforms to a resolved non-output value and map it to its container
        path.

        Used for top-level, fingerprint param, option and input specs. Applies the
        spec's `transform` (scenario_name, filename), then maps mounted TypedPaths and str/Path values to container paths.

        Args:
            value: Resolved value from the arg's source (or an alternative)
            arg_spec: Argument specification from the module YAML

        Returns:
            The transformed value; a container path string (or list of them) for
            mounted paths, otherwise the value unchanged.
        """
        # Apply transform if specified
        transform = _transform_of(arg_spec)
        mount = arg_spec.mount
        mount_volume = mount.volume if mount else None
        if transform == "scenario_name":
            if hasattr(value, "scenario_name"):
                value = value.scenario_name
            elif isinstance(value, dict):
                value = value.get("scenario_name", value.get("scenario", value))
        elif transform == "filename":
            # Skip for output-volume args that are paths under output root (e.g. fair-temperature/climate.nc).
            if isinstance(value, (str, Path)) and not (
                mount_volume == self.module_definition.output_volume_key()
                and "/" in str(value)
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

        # Handle mount transformations for file paths.
        if mount and isinstance(value, (str, Path)):
            container_path = mount.container_path.rstrip("/")
            if (
                container_path
                and mount_volume == self.module_definition.output_volume_key()
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

    def _build_volumes(self) -> list[str]:
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
            if not host_path_source:
                continue

            # Resolve host path from module_inputs
            host_path = self._resolve_value(SourcePath.parse(host_path_source))
            if host_path is None:
                continue
            host_path = str(Path(host_path).resolve())
            # For the output volume: mount the shared output root (parent of per-module dir)
            # so source is .../output and dest is /mnt/out; container paths use /mnt/out/<module_name>/...
            if volume_name == self.module_definition.output_volume_key():
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

    def _get_dependency_names(
        self, climate_service_name: str | None = None
    ) -> list[str]:
        """Return resolved service names this module depends on.

        Format-agnostic: returns names only, without condition metadata.
        Useful for dependency-graph calculations where only the names matter
        (e.g. stage grouping for Apptainer). For the Docker Compose depends_on
        dict, use _build_compose_depends_on() instead.
        """
        names: list[str] = []

        if self.module_definition.uses_climate_file and climate_service_name:
            names.append(climate_service_name)

        for dep_spec in self.module_definition.depends_on or []:
            if isinstance(dep_spec, dict):
                service_name = dep_spec.get("service", "")
                if service_name:
                    if service_name == "fair" and climate_service_name:
                        service_name = climate_service_name
                    names.append(service_name)
            elif isinstance(dep_spec, str):
                mapped = dep_spec
                if dep_spec == "fair" and climate_service_name:
                    mapped = climate_service_name
                names.append(mapped)

        return names

    def _build_compose_depends_on(
        self, climate_service_name: str | None = None
    ) -> dict[str, Any]:
        """Build the Docker Compose depends_on dict from dependency configuration.

        Compose-specific: wraps each dependency name with a condition dict.
        If uses_climate_file is True, automatically adds dependency on the
        climate service. Also processes explicit depends_on entries from YAML.

        For format-agnostic dependency names only, use _get_dependency_names().
        """
        depends_on: dict[str, Any] = {}

        if self.module_definition.uses_climate_file and climate_service_name:
            depends_on[climate_service_name] = {
                "condition": "service_completed_successfully"
            }

        for dep_spec in self.module_definition.depends_on or []:
            if isinstance(dep_spec, dict):
                service_name = dep_spec.get("service", "")
                condition = dep_spec.get("condition", "service_completed_successfully")
                if service_name:
                    if service_name == "fair" and climate_service_name:
                        service_name = climate_service_name
                    depends_on[service_name] = {"condition": condition}
            elif isinstance(dep_spec, str):
                mapped = dep_spec
                if dep_spec == "fair" and climate_service_name:
                    mapped = climate_service_name
                depends_on[mapped] = {"condition": "service_completed_successfully"}

        return depends_on

    def _build_environment(self) -> dict[str, str]:
        """Build environment variable dict for args declared with envvar in the module
        YAML.

        For each input arg that has an `envvar` key, the resolved container-path value
        (if any) is added to the environment dict under the declared variable name. Args
        with no resolvable value are omitted — the container's own defaults or host
        environment handle them.
        """
        environment: dict[str, str] = {}
        for arg_spec in self.module_definition.arguments.inputs:
            if not arg_spec.envvar:
                continue
            value = self._process_argument(arg_spec)
            if value is not None:
                environment[arg_spec.envvar] = str(value)
        return environment

    def generate_compose_service(
        self,
        climate_service_name: str | None = None,
        suppress_output_types: set | None = None,
    ) -> dict[str, Any]:
        """Generate Docker Compose service configuration.

        Args:
            climate_service_name: Optional name of the climate service (e.g., "fair-climate") to map "fair" dependencies to

        Returns:
            Dictionary representing a Docker Compose service
        """
        image_str = (
            f"{self.components.image.image_url}:{self.components.image.image_tag}"
        )
        command = self._build_command_args(suppress_output_types=suppress_output_types)
        volumes = self._build_volumes()
        depends_on = self._build_compose_depends_on(
            climate_service_name=climate_service_name
        )
        environment = self._build_environment()
        return build_compose_service_dict(
            image_str=image_str,
            command=command,
            volumes=volumes,
            depends_on=depends_on,
            environment=environment,
        )

    def generate_asyncflow_config(self) -> dict[str, Any]:
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


def _resolve_module_inputs_dict(
    module_definition: ModuleSchema,
    module_name_str: str,
    module_inputs_section: dict,
    shared_input_data: str,
    module_specific_input_data: str,
    experiment_specific_input_data: str | None,
    module_name: str,
):
    # Inputs that mount from the shared output volume produced by another service (such as
    # fair-temperature). They're stored as relative paths (e.g. fair-temperature/climate.nc
    # -> /mnt/out/fair-temperature/climate.nc). Keyed by `name`, matching how the persisted
    # experiment-config.yaml `inputs` section (module_inputs_section) is keyed.
    output_root_relative_inputs = module_definition.get_output_volume_input_keys()

    inputs_dict = {}
    for arg_spec in module_definition.arguments.inputs:
        name = arg_spec.name
        if not name or name not in module_inputs_section:
            continue
        value = module_inputs_section[name]

        # `key` is the internal resolution key: the arg-spec's own `source` suffix (e.g.
        # "module_inputs.inputs.climate_data_file" -> "climate_data_file"), which is what
        # `ModuleServiceSpecComponents.resolve()`/other arg-specs' `source` fields
        # address this value by. It is NOT necessarily the same string as `name`.
        key = arg_spec.source.leaf

        mount = arg_spec.mount
        is_multiple = arg_spec.multiple and (
            mount is not None or arg_spec.type == "file"
        )
        is_dir = arg_spec.type == "dir"

        if is_multiple:
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
                            field_name=name,
                            field_value=item_value,
                            mount=mount,
                            shared_input_data=shared_input_data,
                            module_specific_input_data=module_specific_input_data,
                            module_name=module_name,
                            context=module_name_str,
                        )
                    )
                except (ValueError, KeyError, TypeError) as e:
                    error_msg = str(e)
                    if "None" in error_msg or "NoneType" in error_msg:
                        raise ValueError(
                            f"Input field '{name}' in {module_name_str} has None value or None in path resolution. "
                            f"Original error: {error_msg}. "
                            f"Check that '{name}' has a valid value in metadata.{module_name}.inputs"
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
                name in output_root_relative_inputs
                and isinstance(actual, str)
                and actual.strip()
                and not actual.strip().startswith("/")
                and ".." not in actual
            ):
                inputs_dict[key] = actual.strip()  # e.g. "fair-temperature/climate.nc"
                continue
            if (
                name in output_root_relative_inputs
                and isinstance(actual, str)
                and actual.strip().startswith("/")
                and experiment_specific_input_data
            ):
                inputs_dict[key] = ExperimentSpecificInputPath(actual.strip())
                continue
            try:
                resolved_path = resolve_input_path(
                    field_name=name,
                    field_value=value,
                    mount=mount,
                    shared_input_data=shared_input_data,
                    module_specific_input_data=module_specific_input_data,
                    module_name=module_name,
                    context=module_name_str,
                )
                inputs_dict[key] = (
                    HostDirPath(resolved_path) if is_dir else HostPath(resolved_path)
                )
            except (ValueError, KeyError, TypeError) as e:
                error_msg = str(e)
                if "None" in error_msg or "NoneType" in error_msg:
                    raise ValueError(
                        f"Input field '{name}' in {module_name_str} has None value or None in path resolution. "
                        f"Original error: {error_msg}. "
                        f"Check that '{name}' has a valid value in metadata.{module_name}.inputs"
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
    module_outputs: dict | list,
    module_name_str: str,
    module_name: str,
    output_data_location,
) -> dict:
    outputs_dict = {}
    outputs_config = module_definition.get_outputs_list()

    if isinstance(module_outputs, dict):
        for output_spec in outputs_config:
            output_name = output_spec.name
            key = output_spec.source.leaf
            if not output_name or output_name not in module_outputs:
                raise KeyError(
                    f"Output '{output_name}' not found in metadata for {module_name_str}. "
                    f"Expected one of: {list(module_outputs.keys())}"
                )
            output_value = module_outputs[output_name]
            try:
                resolved_path = resolve_output_path(
                    output_value, output_data_location, module_name_str
                )
                outputs_dict[key] = resolved_path
            except ValueError:
                outputs_dict[key] = output_value
    elif isinstance(module_outputs, list):
        raise ValueError("Expected module_outputs to be dict, instead received list.")

    else:
        raise ValueError(
            f"{module_name}.outputs must be a list or dictionary in {module_name_str}"
        )
    return outputs_dict


def _parse_image(image_data, module_name_str) -> ModuleContainerImage:
    if isinstance(image_data, str):
        if ":" in image_data:
            image_url, image_tag = image_data.rsplit(":", 1)
        else:
            raise ValueError(
                f"Expected ':' in image url to reference version tag. Received '{image_data}"
            )

    else:
        raise ValueError(
            f"invalid image format in {module_name_str}, received: {image_data}."
            f"Expected image_data to be a string, received: {type(image_data)}"
        )
    image = ModuleContainerImage(image_url=image_url, image_tag=image_tag)
    return image


def _assemble_fingerprint_params(module_definition, module_fp_section, location_file):
    """Translate the persisted (name-keyed) fingerprint_params section into the internal
    resolution dict, keyed by each arg-spec's own `source` suffix (see
    `_resolve_module_outputs_dict` for the same pattern)."""
    fingerprint_params = {"location_file": location_file}

    if isinstance(module_fp_section, dict):
        for fp_spec in module_definition.arguments.fingerprint_params:
            name = fp_spec.name
            if not name or name not in module_fp_section:
                continue
            v = module_fp_section[name]
            actual = v.get("value", v) if isinstance(v, dict) else v
            if actual is None:
                continue
            fingerprint_params[fp_spec.source.leaf] = actual
    return fingerprint_params


def build_compose_service_dict(
    image_str: str,
    command: list[str],
    volumes: list[str],
    depends_on: dict[str, Any] | None = None,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a Docker Compose service dictionary from a ModuleServiceSpec.

    Args:
        image_str: Full image string (e.g. "repo/image:tag")
        command: List of command-line argument strings (e.g. ["--pipeline-id=aaa", ...])
        volumes: List of volume mount strings (e.g. ["/host/path:/container/path"])
        depends_on: Optional dict mapping service names to dependency conditions
        environment: Optional dict of environment variables to set in the container

    Returns:
        Dictionary suitable for a single service in a compose file (image, command, volumes, depends_on, restart)
    """
    # TODO: better fix for this but should work for now
    if command and command[0] == "main":
        command = command[1:]
    service = {
        "image": image_str,
        "command": command,
        "volumes": volumes,
        "restart": "no",
    }
    if environment:
        service["environment"] = environment
    if depends_on:
        service["depends_on"] = depends_on
    return service
