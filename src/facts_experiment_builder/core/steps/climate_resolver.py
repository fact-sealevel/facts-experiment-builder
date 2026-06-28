"""Resolve which climate output file a sealevel module should use as input."""

from facts_experiment_builder.core.module.module_schema import ModuleSchema


def resolve_climate_file(climate_schema: ModuleSchema, climate_output_type: str) -> str:
    """Return the relative climate output path a sealevel module should use.

    Searches the climate module's file outputs for one whose name matches
    ``climate_output_type`` and returns ``"{module_name}/{filename}"``.

    Raises ValueError if no matching output is found.
    """
    for output in climate_schema.get_file_outputs():
        if output.get("name") == climate_output_type:
            filename = output.get("filename")
            return f"{climate_schema.module_name}/{filename}"
    raise ValueError(
        f"Climate module '{climate_schema.module_name}' has no output named "
        f"'{climate_output_type}'. Available: "
        f"{[o.get('name') for o in climate_schema.get_file_outputs()]}"
    )
