"""Parser for IPCC AR5 glaciers module."""

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
)
from facts_experiment_builder.core.modules.abcs.abcs import ScenarioConfig
from .module import (
    IPCCAR5GlaciersOptions,
    IPCCAR5GlaciersInputPaths,
    IPCCAR5GlaciersOutputPaths,
    IPCCAR5GlaciersInputs,
    IPCCAR5GlaciersModule,
)

class IPCCAR5GlaciersModuleParser(ModuleParserABC):
    """Parser for IPCC AR5 glaciers module."""

    def get_module_type(self) -> str:
        return "ipccar5-glaciers"

    def parse_from_metadata(self, metadata: Dict[str, Any], experiment_dir: Path):
        """Parse metadata and return IPCCAR5GlaciersModule instance."""
        module_context = "ipccar5-glaciers module"
        
        # Extract scenario (required)
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

        # Create IPCCAR5GlaciersOptions (all fields required)
        ipccar5_glaciers_options = IPCCAR5GlaciersOptions(
            module_name="ipccar5-glaciers",
            scenario=scenario,
            pipeline_id=str(
                get_required_field_with_alternatives(
                    metadata, "pipeline-id", ["pipeline_id"], module_context
                )
            ),
            nsamps=int(get_required_field(metadata, "nsamps", module_context)),
            seed=int(get_required_field(metadata, "seed", module_context)),
            pyear_start=int(get_required_field(metadata, "pyear_start", module_context)),
        )
        
        # Extract input paths (required)
        v2_module_inputs = get_required_field_with_alternatives(
            metadata,
            "v2-module-inputs-paths",
            ["v2_module_inputs_paths"],
            module_context
        )
        # v2_module_inputs["ipccar5-glaciers"] is a list, not a dict, so use get_required_field
        ipccar5_glaciers_inputs_list = get_required_field(
            v2_module_inputs, "ipccar5-glaciers", module_context
        )
        if not isinstance(ipccar5_glaciers_inputs_list, list):
            raise ValueError(
                f"v2-module-inputs-paths -> ipccar5-glaciers must be a list in {module_context}"
            )
        ipccar5_glaciers_input_path = expand_path(
            get_required_list_item(
                ipccar5_glaciers_inputs_list,
                0,
                "v2-module-inputs-paths -> ipccar5-glaciers",
                module_context
            )
        )
        
        # Extract input file names (required)
        glacier_fraction_file = get_required_field(
            metadata, "glacier_fraction_file", module_context
        )
        climate_fname = get_required_field(
            metadata, "climate_fname", module_context
        )
        
        # Create input paths
        ipccar5_glaciers_input_paths = IPCCAR5GlaciersInputPaths(
            ipccar5_glaciers_in_dir=ipccar5_glaciers_input_path,
            ipccar5_glaciers_fraction_file=glacier_fraction_file,
            climate_fname=climate_fname,
        )
        
        # Extract output paths (required)
        v2_output_path = expand_path(
            get_required_field_with_alternatives(
                metadata, "v2-output-path", ["v2_output_path"], module_context
            )
        )
        v2_output_files = get_required_nested_field(
            get_required_field_with_alternatives(
                metadata, "v2-output-files", ["v2_output_files"], module_context
            ),
            ["ipccar5-glaciers"],
            module_context
        )
        
        # Extract output file name (required)
        if not isinstance(v2_output_files, list):
            raise ValueError(
                f"v2-output-files -> ipccar5-glaciers must be a list in {module_context}"
            )
        if len(v2_output_files) == 0:
            raise ValueError(
                f"v2-output-files -> ipccar5-glaciers list is empty in {module_context}"
            )
        ipccar5_glaciers_gslr_output_file = v2_output_files[0]

        # Create output paths
        ipccar5_glaciers_output_paths = IPCCAR5GlaciersOutputPaths(
            ipccar5_glaciers_out_dir=v2_output_path,
            ipccar5_glaciers_gslr_output_file=ipccar5_glaciers_gslr_output_file,
        )
        
        # Get container image (required)
        image = get_required_field(metadata, "ipccar5_image", module_context)
        
        # Create inputs
        ipccar5_glaciers_inputs = IPCCAR5GlaciersInputs(
            options=ipccar5_glaciers_options,
            input_paths=ipccar5_glaciers_input_paths,
            output_paths=ipccar5_glaciers_output_paths,
            image=image,
        )
        
        # Create module
        ipccar5_glaciers_module = IPCCAR5GlaciersModule(module_inputs=ipccar5_glaciers_inputs)
        return ipccar5_glaciers_module