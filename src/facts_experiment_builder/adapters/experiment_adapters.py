from facts_experiment_builder.core.experiment.experiment_skeleton import ExperimentSkeleton
from facts_experiment_builder.core.experiment.facts_experiment import (
    FactsExperiment,
    TopLevelParams,
)
from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleSchema,
    collect_metadata_param_keys,
)
from facts_experiment_builder.core.steps.climate_step import (
    ClimateStep,
)
from facts_experiment_builder.core.steps.sealevel_step import SealevelStep
from facts_experiment_builder.core.steps.totaling_step import TotalingStep
from facts_experiment_builder.core.steps.extreme_sealevel_step import ExtremeSealevelStep
from facts_experiment_builder.core.steps.climate_resolver import resolve_climate_file

from typing import Dict, Optional, Any

def hydrate_experiment(
    skeleton: ExperimentSkeleton,
    schemas: Dict[str, ModuleSchema],
    top_level_context: Optional[Dict[str, Any]] = None,
) -> tuple:
    """From experiment skeleton and dict of modules schemas, return the four hydrated steps of the experiment.

    Errors from unknown module names propagate immediately — no silent failures.
    """
    climate_files: Optional[Dict[str, str]] = None
    sealevel_schemas = None

    # If skeleton has a climate module, extract schema and build step
    if skeleton.climate_module and skeleton.climate_module.upper() != "NONE":
        climate_schema = schemas[skeleton.climate_module]
        climate_step = ClimateStep.from_module_schema(climate_schema)

        # this happens in the climate section in order to match the correct
        # climate input data type for different sealevel modules
        sealevel_schemas = [schemas[name] for name in (skeleton.sealevel_modules or [])]

        climate_files = {
            s.module_name: resolve_climate_file(
                climate_schema, s.get_climate_output_type()
            )
            for s in sealevel_schemas
            if s.get_climate_output_type()
        }
    # Skip climate step or assign alternate data depending on user input
    elif skeleton.supplied_totaled_sealevel_step_data:
        climate_step = ClimateStep.not_needed()
    else:
        climate_step = ClimateStep(alternate_climate_data=skeleton.climate_data)

    # now hydrate sealevel step
    if skeleton.sealevel_modules:
        sealevel_schemas = [schemas[m] for m in skeleton.sealevel_modules]
        sealevel_step = SealevelStep.from_module_schemas(
            schemas=sealevel_schemas,
            climate_files=climate_files,
            module_regions=skeleton.module_regions,
            top_level_context=top_level_context,
        )
    else:
        sealevel_step = SealevelStep(
            supplied_totaled_sealevel_data=skeleton.supplied_totaled_sealevel_step_data
        )

    # Now hydrate totaling step
    if skeleton.totaling_module:
        totaling_step = TotalingStep.from_module_schema(
            schema=schemas[skeleton.totaling_module]
        )
    else:
        totaling_step = TotalingStep()

    # Hydrate esl step
    if skeleton.extremesealevel_module:
        extreme_sealevel_step = ExtremeSealevelStep.from_module_schema(
            schema=schemas[skeleton.extremesealevel_module]
        )
    else:
        extreme_sealevel_step = ExtremeSealevelStep()

    return climate_step, sealevel_step, totaling_step, extreme_sealevel_step


def experiment_skeleton_to_facts_experiment(
    experiment_name: str,
    skeleton: ExperimentSkeleton,
    top_level_params: "TopLevelParams",
    schemas,
    module_specific_input_data: Optional[str] = None,
    experiment_specific_input_data: Optional[str] = None,
    shared_input_data: Optional[str] = None,
    projection_scale: str = "local",
) -> FactsExperiment:
    """
    From skeleton, top level params and module schemas, assemble full facts experiment

    Unknown module names raise FileNotFoundError to avoid no silent failures.
    """
    list_of_schemas = list(schemas.values())

    # Lookup table mapping schema key names (kebab and snake) to CLI-provided values
    cli_values: Dict[str, object] = {
        "pipeline-id": top_level_params.pipeline_id,
        "pipeline_id": top_level_params.pipeline_id,
        "scenario": top_level_params.scenario,
        "baseyear": top_level_params.baseyear,
        "pyear_start": top_level_params.pyear_start,
        "pyear-start": top_level_params.pyear_start,
        "pyear_end": top_level_params.pyear_end,
        "pyear-end": top_level_params.pyear_end,
        "pyear_step": top_level_params.pyear_step,
        "pyear-step": top_level_params.pyear_step,
        "nsamps": top_level_params.nsamps,
        "location-file": top_level_params.location_file,
        "location_file": top_level_params.location_file,
    }

    # Build top-level context for multi-key filename_map resolution in module specs.
    top_level_context = {k: v for k, v in cli_values.items() if v is not None}
    # hydrate skeleton to create steps
    climate_step, sealevel_step, totaling_step, extreme_sealevel_step = (
        hydrate_experiment(
            skeleton, schemas=schemas, top_level_context=top_level_context
        )
    )

    ## This section is for top-level / experiment-level fields
    # it extracts information for top-level params from module yamls
    # and has fixed fields for experiment level params like paths
    top_level_keys = collect_metadata_param_keys(list_of_schemas, "top_level")
    top_level_param_bundles = {
        key: create_metadata_bundle(help_text, cli_values.get(key))
        for key, help_text in top_level_keys.items()
    }

    paths = {
        "module-specific-input-data": create_metadata_bundle(
            "Module-specific input data", module_specific_input_data
        ),
        "shared-input-data": create_metadata_bundle(
            "Shared input data", shared_input_data
        ),
        "experiment-specific-input-data": create_metadata_bundle(
            "Experiment-specific input data (eg. alternative FAIR data)",
            experiment_specific_input_data,
        ),
        "output-data-location": create_metadata_bundle(
            "Output path",
            f"./experiments/{experiment_name}/data/output",
        ),
        **(
            {
                "supplied-totaled-sealevel-step-data": create_metadata_bundle(
                    "Path to pre-existing totaled sealevel data (replaces running climate and sealevel modules)",
                    skeleton.supplied_totaled_sealevel_step_data,
                )
            }
            if skeleton.supplied_totaled_sealevel_step_data
            else {}
        ),
    }

    fp_keys = collect_metadata_param_keys(list_of_schemas, "fingerprint_params")
    fingerprint_params = {
        key: create_metadata_bundle(help_text, cli_values.get(key))
        for key, help_text in fp_keys.items()
    }

    return FactsExperiment(
        experiment_name=experiment_name,
        top_level_params=top_level_param_bundles,
        climate_step=climate_step,
        sealevel_step=sealevel_step,
        totaling_step=totaling_step,
        extreme_sealevel_step=extreme_sealevel_step,
        paths=paths,
        fingerprint_params=fingerprint_params,
        workflows=skeleton.workflows,
        projection_scale=projection_scale,
    )
