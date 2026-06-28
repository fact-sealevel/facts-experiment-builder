"""Tests for SealevelStep."""

from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.steps.sealevel_step import SealevelStep


def _sealevel_schema(module_name: str, uses_climate_file: bool = True) -> ModuleSchema:
    return ModuleSchema(
        module_name=module_name,
        container_image="img:tag",
        uses_climate_file=uses_climate_file,
        arguments={
            "inputs": [
                {
                    "name": "climate-data-file",
                    "type": "str",
                    "source": "module_inputs.inputs.climate_data_file",
                    "mount": {"volume": "output", "container_path": "/mnt/out"},
                }
            ],
            "outputs": {},
        },
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
    )


def test_from_module_schemas_prefills_climate_file_for_matching_module():
    schema = _sealevel_schema("bamber19-icesheets")
    step = SealevelStep.from_module_schemas(
        [schema],
        climate_files={"bamber19-icesheets": "fair-temperature/climate.nc"},
    )
    inputs = step.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value")
        == "fair-temperature/climate.nc"
    )


def test_from_module_schemas_no_prefill_when_module_not_in_climate_files():
    schema = _sealevel_schema("bamber19-icesheets")
    step = SealevelStep.from_module_schemas(
        [schema],
        climate_files={"other-module": "fair-temperature/climate.nc"},
    )
    inputs = step.module_specs_list[0].inputs
    assert (
        inputs.get("climate_data_file", {}).get("value")
        != "fair-temperature/climate.nc"
    )


def test_from_module_schemas_no_prefill_when_climate_files_is_none():
    schema = _sealevel_schema("bamber19-icesheets")
    step = SealevelStep.from_module_schemas([schema], climate_files=None)
    inputs = step.module_specs_list[0].inputs
    assert inputs.get("climate_data_file", {}).get("value") is None


def test_from_module_schemas_prefills_per_module_independently():
    schema_a = _sealevel_schema("module-a")
    schema_b = _sealevel_schema("module-b")
    step = SealevelStep.from_module_schemas(
        [schema_a, schema_b],
        climate_files={
            "module-a": "fair-temperature/climate.nc",
            "module-b": "fair-temperature/gsat.nc",
        },
    )
    inputs_a = step.module_specs_list[0].inputs
    inputs_b = step.module_specs_list[1].inputs
    assert (
        inputs_a.get("climate_data_file", {}).get("value")
        == "fair-temperature/climate.nc"
    )
    assert (
        inputs_b.get("climate_data_file", {}).get("value") == "fair-temperature/gsat.nc"
    )


def test_from_module_schemas_skips_prefill_when_uses_climate_file_false():
    schema = _sealevel_schema("no-climate-module", uses_climate_file=False)
    step = SealevelStep.from_module_schemas(
        [schema],
        climate_files={"no-climate-module": "fair-temperature/climate.nc"},
    )
    inputs = step.module_specs_list[0].inputs
    assert inputs.get("climate_data_file", {}).get("value") is None
