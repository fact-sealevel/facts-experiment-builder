"""Parser for Bamber19 Icesheets module."""

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
    Bamber19Options,
    Bamber19IcesheetsInputPaths,
    Bamber19IcesheetsOutputPaths,
    Bamber19Inputs,
    Bamber19IcesheetsModule,
)


class Bamber19ModuleParser(ModuleParserABC):
    """Parser for Bamber19 Icesheets module."""

    def get_module_type(self) -> str:
        return "bamber19-icesheets"

    def parse_from_metadata(
        self, metadata: Dict[str, Any], experiment_dir: Path
    ):
        """Parse metadata and return Bamber19IcesheetsModule instance."""
        module_context = "bamber19-icesheets module"
        
        # Get module-specific metadata section
        bamber_metadata = get_required_field(metadata, "bamber19-icesheets", module_context)
        
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
        bamber_inputs_section = get_required_field(bamber_metadata, "inputs", module_context)

        # Create Bamber19Options (inherits from SealevelModuleOptions)
        # Top-level fields: pipeline-id, nsamps, seed, scenario, pyear_start, pyear_end, pyear_step, baseyear
        # Module-specific fields from inputs: replace
        bamber_options = Bamber19Options(
            module_name="bamber19-icesheets",
            scenario=scenario,
            pipeline_id=str(
                get_required_field_with_alternatives(
                    metadata, "pipeline-id", ["pipeline_id"], module_context
                )
            ),
            nsamps=int(get_required_field(metadata, "nsamps", module_context)),
            seed=int(get_required_field(metadata, "seed", module_context)),
            pyear_start=int(
                get_required_field_with_alternatives(
                    metadata, "pyear_start", ["pyear-start"], module_context
                )
            ),
            pyear_end=int(
                get_required_field_with_alternatives(
                    metadata, "pyear_end", ["pyear-end"], module_context
                )
            ),
            pyear_step=int(
                get_required_field_with_alternatives(
                    metadata, "pyear_step", ["pyear-step"], module_context
                )
            ),
            baseyear=int(get_required_field(metadata, "baseyear", module_context)),
            replace=bool(get_required_field(bamber_inputs_section, "replace", module_context)),
        )

        # Extract input paths (required)
        bamber19_input_path = expand_path(
            get_required_field(bamber_inputs_section, "input_dir", module_context)
        )

        # Extract input file names (required)
        slr_proj_mat_file = get_required_field(
            bamber_inputs_section, "slr_proj_mat_file", module_context
        )
        climate_data_file = get_required_field(
            bamber_inputs_section, "climate_data_file", module_context
        )

        # Create input paths
        input_paths = Bamber19IcesheetsInputPaths(
            bamber19_icesheets_in_dir=bamber19_input_path,
            bamber19_slr_proj_mat_file=slr_proj_mat_file,
            climate_data_file=climate_data_file,
        )

        # Extract output path from top-level
        v2_output_path = expand_path(
            get_required_field_with_alternatives(
                metadata, "v2-output-path", ["v2_output_path"], module_context
            )
        )
        
        # Get outputs from module-specific section
        bamber_outputs = get_required_field(bamber_metadata, "outputs", module_context)
        if not isinstance(bamber_outputs, list):
            raise ValueError(
                f"bamber19-icesheets.outputs must be a list in {module_context}"
            )
        if len(bamber_outputs) < 4:
            raise ValueError(
                f"bamber19-icesheets.outputs must have at least 4 items "
                f"(found {len(bamber_outputs)}) in {module_context}"
            )
        # Assume outputs are in order: ais, eais, wais, gis
        ais_gslr = bamber_outputs[0]
        eais_gslr = bamber_outputs[1]
        wais_gslr = bamber_outputs[2]
        gis_gslr = bamber_outputs[3]

        # Create output paths
        output_paths = Bamber19IcesheetsOutputPaths(
            bamber19_icesheets_out_dir=v2_output_path,
            bamber_ais_gslr_fname=ais_gslr,
            bamber_eais_gslr_fname=eais_gslr,
            bamber_wais_gslr_fname=wais_gslr,
            bamber_gis_gslr_fname=gis_gslr,
        )

        # Get image from module-specific section
        image = get_required_field(bamber_metadata, "image", module_context)

        # Create Bamber19Inputs
        bamber_inputs = Bamber19Inputs(
            bamber_options=bamber_options,
            input_paths=input_paths,
            output_paths=output_paths,
            image=image,
        )

        # Create module instance
        module = Bamber19IcesheetsModule(module_inputs=bamber_inputs)

        return module

