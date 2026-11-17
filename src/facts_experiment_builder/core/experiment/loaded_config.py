"""Read-side view of an experiment-config.yaml file, as returned by
ExperimentRepository.get().

This is distinct from experiment_config.ExperimentConfig, which holds what setup-
experiment renders into the YAML template.
"""

from dataclasses import dataclass, field
from typing import Any


# Fields that must have a value, mapped to their experiment-config.yaml key (used in
# error messages).
_REQUIRED_FIELDS = {
    "experiment_name": "experiment_name",
    "pipeline_id": "pipeline-id",
    "nsamps": "nsamps",
    "scenario": "scenario",
    "baseyear": "baseyear",
    "pyear_start": "pyear_start",
    "pyear_end": "pyear_end",
    "pyear_step": "pyear_step",
    "module_specific_input_data": "module-specific-input-data",
    "shared_input_data": "shared-input-data",
}
_INT_FIELDS = ("nsamps", "baseyear", "pyear_start", "pyear_end", "pyear_step")
# Required fields whose values must be strings.
_STR_FIELDS = (
    "experiment_name",
    "pipeline_id",
    "scenario",
    "module_specific_input_data",
    "shared_input_data",
)
# Optional fields that must be strings when present.
_OPTIONAL_STR_FIELDS = ("climate_module", "projection_scale", "location_file")
# Raw experiment-config.yaml keys captured as typed fields above (or read as
# module sections / module_schemas). Anything else in the file lands in
# LoadedExperimentConfig.other_top_level_values.
_CAPTURED_YAML_KEYS = {
    "experiment_name",
    "projection_scale",
    "pipeline-id",
    "nsamps",
    "scenario",
    "baseyear",
    "pyear_start",
    "pyear_end",
    "pyear_step",
    "location-file",
    "climate_module",
    "sealevel_modules",
    "framework_modules",
    "esl_modules",
    "workflows",
    "module-specific-input-data",
    "shared-input-data",
    "experiment-specific-input-data",
    "supplied-totaled-sealevel-step-data",
    "compose-output-data-location",
    "apptainer-output-data-location",
    "output-data-location",
    "module_registry_version",
    "module_schemas",
}


def _str_list(value: Any) -> list[str]:
    """Return the string entries of a list-valued manifest key (None -> [])."""
    return [m for m in (value or []) if isinstance(m, str)]


def _manifest_module_names(
    climate_module: str | None,
    sealevel_modules: list[str],
    framework_modules: list[str],
    esl_modules: list[str],
) -> list[str]:
    names: list[str] = []
    if climate_module and str(climate_module).upper() != "NONE":
        names.append(str(climate_module))
    return names + sealevel_modules + framework_modules + esl_modules


@dataclass(frozen=True)
class LoadedExperimentConfig:
    """Typed access to a loaded experiment-config.yaml.

    The fields in _REQUIRED_FIELDS must have a value, and the integer fields must be
    ints; __post_init__ raises ValueError otherwise. Other values are taken as loaded,
    without coercion, and are None if their key is missing. Path values are checked and
    expanded later by resolve_experiment_data_paths().

    Keys in the file that are not captured as fields, module sections or
    module_schemas are kept in other_top_level_values, so nothing loaded is dropped.
    """

    experiment_name: str
    projection_scale: str | None
    pipeline_id: str
    nsamps: int
    scenario: str
    baseyear: int
    pyear_start: int
    pyear_end: int
    pyear_step: int
    location_file: str | None

    climate_module: str | None
    sealevel_modules: list[str]
    framework_modules: list[str]
    esl_modules: list[str]
    workflows: dict[str, Any]

    module_specific_input_data: str
    shared_input_data: str
    experiment_specific_input_data: Any
    # Output locations: each run command requires its own (see
    # module_service_path_resolution.output_location(), which reads these fields).
    compose_output_data_location: str | None
    apptainer_output_data_location: str | None
    output_data_location: str | None  # deprecated; read as the Compose location

    # Retained for provenance: not read yet; intended to be written as a comment
    # into files produced by generate-compose / generate-apptainer.
    module_registry_version: str | None
    module_sections: dict[str, dict[str, Any]]
    module_schemas: dict[str, Any] | None

    # The full loaded mapping. Retained for now: the service-spec building
    # chain (prepare_plan -> _build_module_specs / build_experiment_execution_plan)
    # still consumes per-module sections from it.
    raw: dict[str, Any] = field(repr=False)

    # Supplied totaled sea-level step data, when the totaling step is bypassed
    # with pre-existing data instead of sea-level modules.
    supplied_totaled_sealevel_step_data: Any = None
    # Top-level keys not captured above (and not module sections/schemas), e.g.
    # schema-specific top-level params. Transitional: lets consumers that derived
    # values from the raw mapping keep doing so without the raw mapping itself.
    other_top_level_values: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the loaded values, raising ValueError naming the YAML key at fault.

        Checks that every required field has a value, the integer fields hold
        ints (bool is not accepted), the string fields hold strings, and
        workflows / module_schemas hold mappings when present. Other values are
        taken as loaded; path values are expanded later by
        resolve_experiment_data_paths().
        """
        missing = [
            key for name, key in _REQUIRED_FIELDS.items() if getattr(self, name) is None
        ]
        if missing:
            raise ValueError(
                f"experiment-config.yaml is missing values for: {', '.join(missing)}. "
                "Check that all required fields in this experiment's "
                "experiment-config.yaml have been completed."
            )
        not_int = [
            f"{_REQUIRED_FIELDS[name]} ({getattr(self, name)!r})"
            for name in _INT_FIELDS
            if not isinstance(getattr(self, name), int)
            or isinstance(getattr(self, name), bool)
        ]
        if not_int:
            raise ValueError(
                f"experiment-config.yaml values must be integers: {', '.join(not_int)}."
            )
        not_str = [
            f"{_REQUIRED_FIELDS[name]} ({getattr(self, name)!r})"
            for name in _STR_FIELDS
            if not isinstance(getattr(self, name), str)
        ]
        not_str += [
            f"{name} ({getattr(self, name)!r})"
            for name in _OPTIONAL_STR_FIELDS
            if getattr(self, name) is not None
            and not isinstance(getattr(self, name), str)
        ]
        if not_str:
            raise ValueError(
                f"experiment-config.yaml values must be strings: {', '.join(not_str)}."
            )
        if not isinstance(self.workflows, dict):
            raise ValueError(
                "experiment-config.yaml 'workflows' must be a mapping of workflow "
                f"names to module lists, got {self.workflows!r}."
            )
        if self.module_schemas is not None and not isinstance(
            self.module_schemas, dict
        ):
            raise ValueError(
                "experiment-config.yaml 'module_schemas' must be a mapping of "
                f"module names to schemas, got {self.module_schemas!r}."
            )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LoadedExperimentConfig":
        """Build from the mapping loaded from experiment-config.yaml."""
        if not isinstance(raw, dict):
            raise ValueError(
                "experiment-config.yaml is empty or is not a mapping of keys to values."
            )
        climate_module = raw.get("climate_module")
        sealevel_modules = _str_list(raw.get("sealevel_modules"))
        framework_modules = _str_list(raw.get("framework_modules"))
        esl_modules = _str_list(raw.get("esl_modules"))
        module_names = _manifest_module_names(
            climate_module, sealevel_modules, framework_modules, esl_modules
        )

        return cls(
            experiment_name=raw.get("experiment_name"),
            projection_scale=raw.get("projection_scale"),
            pipeline_id=raw.get("pipeline-id"),
            nsamps=raw.get("nsamps"),
            scenario=raw.get("scenario"),
            baseyear=raw.get("baseyear"),
            pyear_start=raw.get("pyear_start"),
            pyear_end=raw.get("pyear_end"),
            pyear_step=raw.get("pyear_step"),
            location_file=raw.get("location-file"),
            climate_module=climate_module,
            sealevel_modules=sealevel_modules,
            framework_modules=framework_modules,
            esl_modules=esl_modules,
            workflows=raw.get("workflows") or {},
            module_specific_input_data=raw.get("module-specific-input-data"),
            shared_input_data=raw.get("shared-input-data"),
            experiment_specific_input_data=raw.get("experiment-specific-input-data"),
            compose_output_data_location=raw.get("compose-output-data-location"),
            apptainer_output_data_location=raw.get("apptainer-output-data-location"),
            output_data_location=raw.get("output-data-location"),
            module_registry_version=raw.get("module_registry_version"),
            module_sections={
                name: raw[name]
                for name in module_names
                if isinstance(raw.get(name), dict)
            },
            module_schemas=raw.get("module_schemas"),
            raw=raw,
            supplied_totaled_sealevel_step_data=raw.get(
                "supplied-totaled-sealevel-step-data"
            ),
            other_top_level_values={
                k: v
                for k, v in raw.items()
                if k not in _CAPTURED_YAML_KEYS and k not in module_names
            },
        )

    @property
    def module_names(self) -> list[str]:
        """All module names in the manifest, in step order.

        A climate module of NONE (any case) is left out.
        """
        return _manifest_module_names(
            self.climate_module,
            self.sealevel_modules,
            self.framework_modules,
            self.esl_modules,
        )
