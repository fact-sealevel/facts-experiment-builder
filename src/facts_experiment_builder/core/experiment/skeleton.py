"""Intent data for a new experiment, built from CLI inputs before YAML loading."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.experiment.module_name_validation import (
    parse_module_list_str,
)
from facts_experiment_builder.core.steps import (
    ClimateStep,
    SealevelStep,
    TotalingStep,
    ExtremeSealevelStep,
)
from facts_experiment_builder.core.components.metadata_bundle import (
    create_metadata_bundle,
)
from facts_experiment_builder.core.steps.climate_resolver import resolve_climate_file
from facts_experiment_builder.core.module.module_schema import (
    collect_metadata_param_keys,
)
from facts_experiment_builder.core.experiment.experiment import (
    FactsExperiment,
    TopLevelParams,
)


def is_totaling_needed(sealevel_step: str) -> bool:
    sealevel_module_ls = parse_module_list_str(s=sealevel_step)

    return len(sealevel_module_ls) > 1


def parse_module_regions(module_regions_args: tuple) -> Dict[str, List[str]]:
    """Parse a tuple of 'module-name=R1,R2' strings into {module: [regions]}.

    Accepts the raw value from a Click multiple=True option.
    Example: ("emulandice2-glaciers=RGI01,RGI02",) -> {"emulandice2-glaciers": ["RGI01", "RGI02"]}
    """
    result: Dict[str, List[str]] = {}
    for entry in module_regions_args or ():
        if "=" not in entry:
            raise ValueError(
                f"Invalid --module-regions format '{entry}'. "
                "Expected 'module-name=REGION1,REGION2'."
            )
        module_name, regions_str = entry.split("=", 1)
        regions = [r.strip() for r in regions_str.split(",") if r.strip()]
        if not regions:
            raise ValueError(
                f"No regions specified for module '{module_name}' in --module-regions."
            )
        result[module_name.strip()] = regions
    return result


@dataclass(frozen=True)
class ExperimentSkeleton:
    """Captures module names / data paths and workflows from CLI inputs.

    Created in the CLI before workflow collection and before any module YAMLs are
    loaded.  Pass to ``hydrate_experiment()`` in the application layer to produce a
    fully-formed ``FactsExperiment``.
    """

    climate_module: Optional[str] = None  # None if data provided
    climate_data: Optional[str] = None  # None if module provided
    sealevel_modules: List[str] = None  # [] if data provided
    supplied_totaled_sealevel_step_data: Optional[str] = (
        None  # None if modules provided
    )
    totaling_module: Optional[str | None] = None  # None if no totaling step
    extremesealevel_module: Optional[str] = None  # None if no ESL step
    workflows: Dict[str, str] = field(default_factory=dict)
    module_regions: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def from_inputs(
        cls,
        climate_step: Optional[str],
        supplied_climate_step_data: Optional[str],
        sealevel_step: Optional[str],
        supplied_totaled_sealevel_step_data: Optional[str],
        extremesealevel_step: Optional[str],
        module_regions: Optional[Dict[str, List[str]]] = None,
    ) -> "ExperimentSkeleton":
        """Build a skeleton by parsing comma-separated CLI module strings."""
        from facts_experiment_builder.core.experiment.module_name_validation import (
            parse_module_list_str,
        )

        # validate climate step inputs
        if not supplied_totaled_sealevel_step_data:
            if climate_step and supplied_climate_step_data:
                raise ValueError(
                    "Pass either a climate module (--climate-step) or climate data "
                    "(--supplied-climate-step-data), not both."
                )
            if not climate_step and not supplied_climate_step_data:
                raise ValueError(
                    "Must pass either a climate module (--climate-step) or climate data "
                    "(--supplied-climate-step-data)."
                )
        # validate sealevel step data
        if sealevel_step and supplied_totaled_sealevel_step_data:
            raise ValueError(
                "Pass either sea-level modules (--sealevel-step) or totaled sea-level data "
                "(--supplied-totaled-sealevel-step-data), not both."
            )

        climate_modules = parse_module_list_str(climate_step)
        sealevel_modules = parse_module_list_str(sealevel_step)
        esl_modules = parse_module_list_str(extremesealevel_step)

        # Domain rules:
        # - totaling can't run if sealevel step bypassed
        # - totaling doesn't run if no sealevel modules are passed
        # - totaling runs if more than one sealevel module included
        if supplied_totaled_sealevel_step_data or not sealevel_modules:
            totaling_module = None
        else:
            totaling_module = "facts-total"
        if not supplied_totaled_sealevel_step_data and not sealevel_modules:
            totaling_module = None
        elif sealevel_modules:
            if len(sealevel_modules) >= 1:
                totaling_module = "facts-total"
        return cls(
            climate_module=climate_modules[0] if climate_modules else None,
            climate_data=supplied_climate_step_data,
            sealevel_modules=sealevel_modules,
            supplied_totaled_sealevel_step_data=supplied_totaled_sealevel_step_data,
            totaling_module=totaling_module,
            extremesealevel_module=esl_modules[0] if esl_modules else None,
            module_regions=module_regions or {},
        )

    @property
    def all_module_names(self) -> List[str]:
        """All module names across all steps (excludes data-only steps)."""
        names: List[str] = []
        if self.climate_module:
            names.append(self.climate_module)
        names.extend(self.sealevel_modules)
        if self.totaling_module:
            names.append(self.totaling_module)
        if self.extremesealevel_module:
            names.append(self.extremesealevel_module)
        return names


def hydrate_experiment(
    skeleton: ExperimentSkeleton,
    schemas: Dict[str, ModuleSchema],
    top_level_context: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Hydrate experiment steps from an ExperimentSkeleton object and modules schemas.

    Resolves the climate, sealevel, totaling, extreme sealevel steps by looking up each module named in `skeleton` within `schemas, then delegating to the corresponding step's `.from_module_schemas(s)` constructor. Steps whose module is unset (or, `"NONE"`) are hydrated from alternate data supplied by user.

    Parameters
    ----------
    skeleton: ExperimentSkeleton
        The experiment skeleton describing which modules to user for each step (climate, sealevel, totaling, extreme sealevel) along with any alternate/supplied data and region overrides.
    schemas: Dict of {str: ModuleSchema}
        Mapping fro module name to its loaded schema, used to look up the schema for each module named in `skeleton`.
    top_level_context: dict of {str: Any}, optional
        Additional context passed through to sealevel step hydration.
        Default is None

    Returns:
    --------
    climate_step: ClimateStep
        Hydrated from `skeleton.climate_module`'s schema if present and not `"NONE"`; otherwise, built from `skeleton.climate_data` or marked as not needed when totaled sealevel data was supplied directly.
    sealevel_step: SealevelStep
        Hydrated from the schemas of `skeleton.sealevel_module` if present, using `climate_files` resolved during climate step hydration; otherwise built from `skeleton.supplied_totaled_sealevel_step_data`. For module regions, uses values specified by user attached to skeleton object.
    totaling_step: TotalingStep
        Hydrated from `skeleton.totaling_module`'s schema if present; otherwise a default-constructed step.
    extreme_sealevel_step: `ExtremeSealevelStep
        Hydrated from `skeleton.extremesealevel_module`'s schema if present; otherwise a default-constructed step.

    Raises
    ------
    KeyError
        If a module name referenced by `skeleton` is not present in `schemas`. Propagates immediately instead of silent failures.
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
    schemas: Dict[str, ModuleSchema],
    experiment_path: Path,
    module_specific_input_data: Optional[str] = None,
    experiment_specific_input_data: Optional[str] = None,
    shared_input_data: Optional[str] = None,
    projection_scale: str = "local",
) -> FactsExperiment:
    """Assemble a FactsExperiment object from an ExperimentSkeleton, top-level params
    and module schemas. Hydrates experiment steps via `hydrate_experiment()`, extracts
    top-level and fingerprint parameter metadata from module schemas, resolves
    input/output data paths and organizes everything into a `FactsExperiment` object.

    Parameters
    ----------
    experiment_name: str
        Name of experiment, used to derive output data path
    skeleton: ExperimentSkeleton
        The experiment skeleton describing which modules or supplied data to use for each step along with workflows and module regions specified by user.
    top_level_params: TopLevelParams
        Values for top-level parameters specified by user via CLI (includes pipeline_id, scenario, baseyear, pyear_start, pyear_end, pyear_step, nsamps, location-file). Used to populate `cli_values` and the top-level and fingerprint parameter bundles used in experiment-config.ymal.
    schemas: dict of {str: ModuleSchemas}
        Mapping from module name to its loaded schema. Used to hydrate experiment steps and to collect top-level/fingerprint param keys across all modules.
    module_specific_input_data: str, optional
        Path to module-specific input data, Default is None
    experiment_specific_input_data: str, optional
        Path to experiment-specific input data (e.g. alternate data to use instead of a module at the climate step).
        Default is None
    shared_input_data: str, Optional
        Path to shared input data, Default is None.
    projection_scale: str, optional
        Projection scale for experiment (local or global). Default is `"local"`.
        NOTE: This does not change anything about how individual modules are executed, just what totaling services are created.
        TODO: When we change the fingerprinting step, this will be impacted/part of those changes.

    Returns
    -------
    FactsExperiment
        The fully assembled experiment, including hydrated steps, top-level parameter bundles, fingerprint parameter bundles, resolved paths, workflows and projection scales.

    Raises
    ------
    FileNotFoundError
        If `skeleton` references a module name not present in `schemas`.
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
            Path(experiment_path, "output").as_posix(),
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
