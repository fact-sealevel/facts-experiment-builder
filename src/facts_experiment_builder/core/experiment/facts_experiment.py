"""In-memory representation of an experiment (analogous to experiment-config.yaml)."""

from typing import Dict, Any, List, Optional

from facts_experiment_builder.core.workflow.workflow import (
    Workflow,
)
from facts_experiment_builder.core.steps import (
    ClimateStep,
    ExperimentStep,
    SealevelStep,
    TotalingStep,
    ExtremeSealevelStep,
    steps_from_metadata,
)


# Keys that appear in experiment-config.yaml (for parsing and round-trip)
TOP_LEVEL_PARAM_KEYS = [
    "pipeline-id",
    "scenario",
    "baseyear",
    "pyear_start",
    "pyear_end",
    "pyear_step",
    "nsamps",
    "seed",
]
MANIFEST_KEYS = [
    "temperature_module",
    "sealevel_modules",
    "framework_modules",
    "esl_modules",
]
PATH_KEYS_PRIMARY = [
    "shared-input-data",
    "module-specific-input-data",
    "output-data-location",
    "location-file",
]
PATH_KEYS_ALTERNATIVES = {
    "shared-input-data": ["shared_input_data"],
    "module-specific-input-data": ["module_specific_input_data"],
    "output-data-location": ["output_data_location", "output-path", "output_path"],
    "location-file": ["location_file"],
}
FINGERPRINT_PARAM_KEYS = ["fingerprint-dir", "location-file"]


class FactsExperiment:
    """
    In-memory representation of an experiment (analoguous to experiment-config.yaml).
    Used to generate run-environment artifacts (e.g. experiment-compose.yaml).
    Loaded from or written to experiment-config.yaml.
    """

    def __init__(
        self,
        experiment_name: str,
        top_level_params: Dict[str, Any],
        climate_step: ClimateStep,
        sealevel_step: SealevelStep,
        totaling_step: TotalingStep,
        extreme_sealevel_step: ExtremeSealevelStep,
        paths: Dict[str, Any],
        fingerprint_params: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
        workflows: Optional[Dict[str, str]] = None,
    ):
        self._experiment_name = experiment_name
        self._top_level_params = dict(top_level_params)
        self._climate_step = climate_step
        self._sealevel_step = sealevel_step
        self._totaling_step = totaling_step
        self._extreme_sealevel_step = extreme_sealevel_step
        self._paths = dict(paths)
        self._fingerprint_params = dict(fingerprint_params)
        self._extra = dict(extra) if extra is not None else {}
        self._workflows = dict(workflows) if workflows is not None else {}

    @property
    def experiment_name(self) -> str:
        """Name of this experiment."""
        return self._experiment_name

    @property
    def top_level_params(self) -> Dict[str, Any]:
        """Top-level parameters shared across modules
        (pipeline-id, scenario, baseyear, pyear_start, pyear_end, pyear_step, nsamps, seed).
        """
        return self._top_level_params

    @property
    def climate_step(self) -> ClimateStep:
        return self._climate_step

    @property
    def sealevel_step(self) -> SealevelStep:
        return self._sealevel_step

    @property
    def totaling_step(self) -> TotalingStep:
        return self._totaling_step

    @property
    def extreme_sealevel_step(self) -> ExtremeSealevelStep:
        return self._extreme_sealevel_step

    def list_all_steps(self) -> List[ExperimentStep]:
        """All experiment steps in order: climate → sealevel → totaling → ESL."""
        return [
            self._climate_step,
            self._sealevel_step,
            self._totaling_step,
            self._extreme_sealevel_step,
        ]

    @property
    def paths(self) -> Dict[str, Any]:
        """Paths to the input and output data for this experiment."""
        return self._paths

    @property
    def fingerprint_params(self) -> Dict[str, Any]:
        """Fingerprint parameters (fingerprint-dir, location-file)."""
        return self._fingerprint_params

    @property
    def extra(self) -> Dict[str, Any]:
        return self._extra

    @property
    def workflows(self) -> Dict[str, str]:
        """Workflows for facts-total: workflow name -> comma-separated module list."""
        return self._workflows

    def get_workflows_as_objects(self) -> Dict[str, Workflow]:
        """Workflows as Workflow instances (name -> Workflow)."""
        return {
            name: Workflow.from_dict(name, value)
            for name, value in self._workflows.items()
        }

    @classmethod
    def from_metadata_dict(cls, metadata: Dict[str, Any]) -> "FactsExperiment":
        """Build a FactsExperiment from the metadata dict shape (e.g. from YAML)."""

        # First extract top-level fields from the metadata object
        experiment_name = metadata.get("experiment_name", "")

        top_level_params = {
            k: metadata[k] for k in TOP_LEVEL_PARAM_KEYS if k in metadata
        }
        fingerprint_params = {
            k: metadata[k] for k in FINGERPRINT_PARAM_KEYS if k in metadata
        }

        # Then, build a manifest of the modules included in the experiment
        manifest = {
            "temperature_module": metadata.get("temperature_module"),
            "sealevel_modules": metadata.get("sealevel_modules", []),
            "framework_modules": metadata.get("framework_modules", []),
            "esl_modules": metadata.get("esl_modules", []),
        }
        if isinstance(manifest["sealevel_modules"], str):
            manifest["sealevel_modules"] = [manifest["sealevel_modules"]]
        if isinstance(manifest["esl_modules"], str):
            manifest["esl_modules"] = [manifest["esl_modules"]]

        # Normalize the paths that are passed in the inputs and outputs sections
        paths_normalized = {}
        for primary in PATH_KEYS_PRIMARY:
            value = metadata.get(primary)
            if value is None and primary in PATH_KEYS_ALTERNATIVES:
                for alt in PATH_KEYS_ALTERNATIVES[primary]:
                    value = metadata.get(alt)
                    if value is not None:
                        break
            if value is not None:
                if isinstance(value, dict) and "clue" in value:
                    paths_normalized[primary] = value
                else:
                    if isinstance(value, dict) and "value" in value:
                        value = value["value"]
                    if isinstance(value, str):
                        paths_normalized[primary] = value
        # Make tuple of the fields that wont' be used to build module_sections
        excluded = (
            set(TOP_LEVEL_PARAM_KEYS)
            | set(FINGERPRINT_PARAM_KEYS)
            | set(MANIFEST_KEYS)
            | set(PATH_KEYS_PRIMARY)
        )
        excluded |= set().union(
            *(PATH_KEYS_ALTERNATIVES.get(k, []) for k in PATH_KEYS_PRIMARY)
        )
        excluded.add("experiment_name")
        excluded.add("workflows")

        workflows = metadata.get("workflows")
        if not isinstance(workflows, dict):
            workflows = {}

        module_sections = {
            k: v
            for k, v in metadata.items()
            if k not in excluded and isinstance(v, dict)
        }

        # Infer esl_modules from module sections when not set (backward compatibility)
        if not manifest["esl_modules"]:
            manifest["esl_modules"] = [
                k
                for k in module_sections
                if isinstance(k, str) and k.startswith("extremesealevel-")
            ]

        extra = {
            k: v
            for k, v in metadata.items()
            if k not in top_level_params
            and k not in manifest
            and k not in paths_normalized
            and k not in fingerprint_params
            and k not in module_sections
            and k != "experiment_name"
            and k != "workflows"
        }

        climate_step, sealevel_step, totaling_step, extreme_sealevel_step = (
            steps_from_metadata(manifest, module_sections)
        )

        return cls(
            experiment_name=experiment_name,
            top_level_params=top_level_params,
            climate_step=climate_step,
            sealevel_step=sealevel_step,
            totaling_step=totaling_step,
            extreme_sealevel_step=extreme_sealevel_step,
            paths=paths_normalized,
            fingerprint_params=fingerprint_params,
            extra=extra,
            workflows=workflows,
        )

    def merge_defaults_for_module(
        self,
        module_name: str,
        defaults_yml: Dict[str, Any],
        module_def: Optional[Any],
    ) -> None:
        """
        Merge defaults from defaults_yml into this experiment's module section.
        Delegates to the step that owns the named module.
        """
        if not defaults_yml:
            return
        if self._climate_step.module_name == module_name:
            self._climate_step.merge_defaults(defaults_yml, module_def)
        elif module_name in self._sealevel_step.module_names:
            self._sealevel_step.merge_defaults_for_module(
                module_name, defaults_yml, module_def
            )
        elif self._totaling_step.module_name == module_name:
            self._totaling_step.merge_defaults(defaults_yml, module_def)
        elif self._extreme_sealevel_step.module_name == module_name:
            self._extreme_sealevel_step.merge_defaults(defaults_yml, module_def)
