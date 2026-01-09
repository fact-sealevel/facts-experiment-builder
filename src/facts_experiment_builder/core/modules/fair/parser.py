"""Parser for FAIR module."""

from typing import Dict, Any
from pathlib import Path

from facts_experiment_builder.adapters.abstract_adapter import (
    ModuleParserABC,
    expand_path,
)
from facts_experiment_builder.adapters.adapter_utils import (
    get_required_field,
    get_required_field_with_alternatives,
    get_required_nested_field,
    get_required_list_item,
    get_required_field_nested_or_top,
)
from facts_experiment_builder.core.modules.abcs.abcs import ScenarioConfig
from .module import (
    FairOptions,
    FairInputPaths,
    FairOutputPaths,
    FairInputs,
    FairModule,
)


class FairModuleParser(ModuleParserABC):
    """Parser for FAIR module."""

    def get_module_type(self) -> str:
        return "fair"

    def parse_from_metadata(
        self, metadata: Dict[str, Any], experiment_dir: Path
    ):
        """Parse metadata and return FairModule instance."""
        module_context = "fair module"
        
        # Get module-specific metadata section
        fair_metadata = get_required_field(metadata, "fair", module_context)
        
        # Extract scenario (required) from top-level
        scenario_name = get_required_field(metadata, "scenario", module_context)
        if isinstance(scenario_name, dict):
            scenario_name = scenario_name.get(
                "scenario_name", scenario_name.get("scenario", "")
            )

        experiment_name = get_required_field(metadata, "experiment_name", module_context)
        scenario = ScenarioConfig(
            scenario_name=scenario_name,
            description=f'Scenario for {experiment_name}',
        )

        # Get inputs section
        fair_inputs_section = get_required_field(fair_metadata, "inputs", module_context)
        
        # Create FairOptions (all fields required)
        # Top-level fields: pipeline-id, nsamps, seed, scenario
        # Module-specific fields from inputs: cyear_start, cyear_end, smooth_win
        fair_options = FairOptions(
            module_name="fair",
            scenario=scenario,
            pipeline_id=str(
                get_required_field_with_alternatives(
                    metadata, "pipeline-id", ["pipeline_id"], module_context
                )
            ),
            nsamps=int(get_required_field(metadata, "nsamps", module_context)),
            seed=int(get_required_field(metadata, "seed", module_context)),
            cyear_start=int(get_required_field(fair_inputs_section, "cyear_start", module_context)),
            cyear_end=int(get_required_field(fair_inputs_section, "cyear_end", module_context)),
            smooth_win=int(get_required_field(fair_inputs_section, "smooth_win", module_context)),
        )

        # Create input paths (all required)
        fair_inputs_dir = expand_path(
            get_required_field(fair_inputs_section, "input_dir", module_context)
        )

        input_paths = FairInputPaths(
            fair_in_dir=fair_inputs_dir,
            rcmip_fname=get_required_field(fair_inputs_section, "rcmip_fname", module_context),
            param_fname=get_required_field(fair_inputs_section, "param_fname", module_context),
        )

        # Get output path from top-level
        v2_output_path = expand_path(
            get_required_field_with_alternatives(
                metadata, "v2-output-path", ["v2_output_path"], module_context
            )
        )
        
        # Get outputs from module-specific section
        fair_outputs = get_required_field(fair_metadata, "outputs", module_context)
        if not isinstance(fair_outputs, list):
            raise ValueError(
                f"fair.outputs must be a list in {module_context}"
            )
        if len(fair_outputs) < 3:
            raise ValueError(
                f"fair.outputs must have at least 3 items "
                f"(found {len(fair_outputs)}) in {module_context}"
            )
        climate_output = fair_outputs[0]
        ohc_output = fair_outputs[1]
        gsat_output = fair_outputs[2]

        output_paths = FairOutputPaths(
            fair_out_dir=v2_output_path,
            ohc_output=ohc_output,
            gsat_output=gsat_output,
            climate_output=climate_output,
        )

        # Get image from module-specific section
        image = get_required_field(fair_metadata, "image", module_context)

        # Create inputs
        fair_inputs = FairInputs(
            fair_options=fair_options,
            input_paths=input_paths,
            output_paths=output_paths,
            image=image,
        )

        # Create module
        fair_module = FairModule(module_inputs=fair_inputs)
        return fair_module

