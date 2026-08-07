from dataclasses import dataclass
from typing import Optional, List, Set, Dict, Any

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.experiment import (
    FactsExperiment,
)
from facts_experiment_builder.core.workflow import Workflow, workflows_from_metadata
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
)
from facts_experiment_builder.core.module.module_schema import (
    collect_metadata_param_keys,
)

_REQUIRED_FIELDS = [
    "experiment_name",
    "pipeline-id",
    "nsamps",
    "scenario",
    "pyear_start",
    "pyear_end",
    "pyear_step",
    "baseyear",
    "module-specific-input-data",
    "shared-input-data",
    "output-data-location",
]


def check_metadata_has_required_fields(metadata_obj, required_fields):
    """This function accepts a list of required fields and a metadata object and subsets
    the metadata to required fields."""
    # Subset
    required_fields_meta = {
        k: v for k, v in metadata_obj.items() if k in required_fields
    }

    # R aise error if any are missing a value
    for k, v in required_fields_meta.items():
        if v is None:
            raise ValueError(
                f"A value for {k} is required but none was found. Check that all required fields in this experiment's experiment-config.yml have been completed."
            )

    return None


@dataclass(frozen=True)
class _ExperimentPlan:
    """Result of phase 1 of gen compose: parsed experiment structure and module name
    lists."""

    experiment: FactsExperiment
    climate_module_name: Optional[str]  # TODO rename to climate
    sealevel_module_names: List[str]
    framework_module_names: List[str]
    esl_module_names: List[str]
    suppress_output_types: Set[str]
    workflows: Dict[str, Workflow]


def _make_experiment_plan(
    metadata: Dict[str, Any], schemas: Dict[str, ModuleSchema]
) -> _ExperimentPlan:
    """Phase 1 of generating compose:
    Validate metadata and build a typed experiment plan.

    Ths fn is only data transformation, there should be no filesystem I/O.
    """
    # This should raise an error if user has not completed necessary fields in experiment-config.yaml
    check_metadata_has_required_fields(
        metadata_obj=metadata, required_fields=_REQUIRED_FIELDS
    )

    # Get the list of modules included in experiment from manifest in exp config
    # _manifest_module_names = _extract_all_module_names_from_manifest(metadata)
    # Use list of modules to load schema for each module
    list_of_schemas = list(schemas.values())
    # Get keys for top level params and fingerprint params from each module in experiment
    _top_level_keys = set(collect_metadata_param_keys(list_of_schemas, "top_level"))
    _fp_keys = set(collect_metadata_param_keys(list_of_schemas, "fingerprint_params"))

    # Create FactsExperiment obj from metadata dict
    experiment = FactsExperiment.from_metadata_dict(
        metadata,
        top_level_keys=_top_level_keys,
        fingerprint_keys=_fp_keys,
    )
    # Set output (local or global) based on user spec. in experiment config
    suppress_output_types: Set[str] = (
        {"local"} if experiment.projection_scale == "global" else set()
    )
    # Separate module names by step
    climate_module_name = experiment.climate_step.module_name or "NONE"
    sealevel_module_names = experiment.sealevel_step.module_names
    framework_module_names = (
        [experiment.totaling_step.module_name]
        if experiment.totaling_step.is_present
        else []
    )
    esl_module_names = (
        [experiment.extreme_sealevel_step.module_name]
        if experiment.extreme_sealevel_step.is_present
        else []
    )
    # Make workflow obj from metadata
    workflows = workflows_from_metadata(metadata)

    # Make an ExperimentPlan obj
    # (first component of generate compose, used to build module spec objs)
    return _ExperimentPlan(
        experiment=experiment,
        climate_module_name=climate_module_name,
        sealevel_module_names=sealevel_module_names,
        framework_module_names=framework_module_names,
        esl_module_names=esl_module_names,
        suppress_output_types=suppress_output_types,
        workflows=workflows,
    )
