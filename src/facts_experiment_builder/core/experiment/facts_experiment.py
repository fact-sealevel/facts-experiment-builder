"""In-memory representation of an experiment (analogous to experiment-config.yaml)."""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
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
from facts_experiment_builder.core.components.metadata_bundle import is_metadata_value


# Framework-level structural keys — these describe the experiment config format,
# not any particular module's parameters.
MANIFEST_KEYS = [
    "temperature_module",
    "sealevel_modules",
    "framework_modules",
    "esl_modules",
]
PATH_KEYS_PRIMARY = [
    "shared-input-data",
    "module-specific-input-data",
    "experiment-specific-input-data",
    "supplied-totaled-sealevel-step-data",
    "output-data-location",
]
PATH_KEYS_ALTERNATIVES = {
    "shared-input-data": ["shared_input_data"],
    "module-specific-input-data": ["module_specific_input_data"],
    "output-data-location": ["output_data_location", "output-path", "output_path"],
}

_STRUCTURAL_KEYS: Set[str] = (
    set(MANIFEST_KEYS)
    | set(PATH_KEYS_PRIMARY)
    | {k for alts in PATH_KEYS_ALTERNATIVES.values() for k in alts}
    | {"experiment_name", "workflows"}
)


def _is_top_level_param_value(value: Any) -> bool:
    """True if value looks like a top-level param (scalar, None, or clue/value bundle)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, dict):
        return is_metadata_value(value)
    return False


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
        self.date_created = datetime.now()
        self.feb_version = None
        self.fmr_version = None

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
    def from_metadata_dict(
        cls,
        metadata: Dict[str, Any],
        top_level_keys: Optional[Set[str]] = None,
        fingerprint_keys: Optional[Set[str]] = None,
    ) -> "FactsExperiment":
        """Build a FactsExperiment from the metadata dict shape (e.g. from YAML).

        Args:
            metadata: Raw dict loaded from experiment-config.yaml.
            top_level_keys: Set of top-level param key names derived from module schemas.
                When omitted, infers by treating any non-structural, non-dict key as a
                top-level param (scalars, None, and clue/value bundles).
            fingerprint_keys: Set of fingerprint param key names derived from module schemas.
                When omitted, defaults to an empty set.
        """
        experiment_name = metadata.get("experiment_name", "")

        if top_level_keys is not None:
            _top_level_keys = top_level_keys
        else:
            _top_level_keys = {
                k
                for k, v in metadata.items()
                if k not in _STRUCTURAL_KEYS and _is_top_level_param_value(v)
            }
        _fp_keys = fingerprint_keys if fingerprint_keys is not None else set()

        top_level_params = {k: metadata[k] for k in _top_level_keys if k in metadata}
        fingerprint_params = {k: metadata[k] for k in _fp_keys if k in metadata}

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
        excluded = _top_level_keys | _fp_keys | _STRUCTURAL_KEYS

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
