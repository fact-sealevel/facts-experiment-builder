"""Tests for facts_experiment_builder.core.module.module_schema."""

from facts_experiment_builder.core.module.module_schema import ModuleSchema


def test_module_schema_construction_minimal():
    """ModuleSchema can be constructed with only required fields."""
    mod = ModuleSchema(
        module_name="test-module",
        container_image="ghcr.io/org/image:0.1.0",
        arguments={},
        volumes={},
    )
    assert mod.module_name == "test-module"
    assert mod.container_image == "ghcr.io/org/image:0.1.0"
    assert mod.arguments == {}
    assert mod.volumes == {}
    assert mod.depends_on is None
    assert mod.command == ""
    assert mod.uses_climate_file is False
    assert mod.extra == {}


def test_module_schema_construction_with_optionals():
    """ModuleSchema accepts optional fields with expected defaults overridable."""
    mod = ModuleSchema(
        module_name="ipccar5-glaciers",
        container_image="ghcr.io/fact-sealevel/ipccar5:0.1.1",
        arguments={"top_level": [], "options": []},
        volumes={
            "module_specific_input": {"host_path": "x", "container_path": "/mnt/in"}
        },
        depends_on=[
            {
                "service": "fair-temperature",
                "condition": "service_completed_successfully",
            }
        ],
        command="glaciers",
        uses_climate_file=True,
        extra={"climate_file_required": True},
    )
    assert mod.module_name == "ipccar5-glaciers"
    assert mod.command == "glaciers"
    assert mod.uses_climate_file is True
    assert mod.depends_on == [
        {"service": "fair-temperature", "condition": "service_completed_successfully"}
    ]
    assert mod.extra == {"climate_file_required": True}
    assert "top_level" in mod.arguments
    assert "module_specific_input" in mod.volumes


def test_module_schema_post_init_normalizes_none_arguments():
    """__post_init__ sets arguments to {} when passed None (if dataclass allows)."""
    # ModuleSchema uses a dataclass with arguments: Dict[...]; passing None can happen from YAML load.
    # The type hint doesn't allow None, but __post_init__ guards for it.
    mod = ModuleSchema(
        module_name="test",
        container_image="img:tag",
        arguments=None,  # type: ignore[arg-type]
        volumes={},
    )
    assert mod.arguments == {}


def test_module_schema_post_init_normalizes_none_volumes():
    """__post_init__ sets volumes to {} when passed None."""
    mod = ModuleSchema(
        module_name="test",
        container_image="img:tag",
        arguments={},
        volumes=None,  # type: ignore[arg-type]
    )
    assert mod.volumes == {}


def test_module_schema_arguments_structure_preserved():
    """Arguments dict structure (top_level, options, inputs, outputs) is preserved."""
    arguments = {
        "top_level": [
            {"name": "scenario", "type": "str", "source": "metadata.scenario"}
        ],
        "options": [],
        "inputs": [
            {
                "name": "climate-data-file",
                "type": "file",
                "source": "module_inputs.inputs.climate_data_file",
            }
        ],
        "outputs": [
            {
                "name": "output-gslr-file",
                "type": "file",
                "source": "module_inputs.outputs.output_gslr_file",
            }
        ],
    }
    mod = ModuleSchema(
        module_name="test",
        container_image="img:tag",
        arguments=arguments,
        volumes={},
    )
    assert mod.arguments == arguments
    assert mod.arguments["top_level"][0]["name"] == "scenario"
    assert len(mod.arguments["inputs"]) == 1
    assert mod.arguments["inputs"][0]["name"] == "climate-data-file"


def test_module_schema_volumes_structure_preserved():
    """Volumes dict structure (host_path, container_path, etc.) is preserved."""
    volumes = {
        "module_specific_input": {
            "host_path": "module_inputs.input_paths.module_specific_input_dir",
            "container_path": "/mnt/module_specific_in",
        },
        "output": {
            "host_path": "module_inputs.output_paths.output_dir",
            "container_path": "/mnt/out",
        },
    }
    mod = ModuleSchema(
        module_name="test",
        container_image="img:tag",
        arguments={},
        volumes=volumes,
    )
    assert mod.volumes == volumes
    assert (
        mod.volumes["module_specific_input"]["container_path"]
        == "/mnt/module_specific_in"
    )


def test_module_schema_extra_default():
    """extra defaults to empty dict and can hold arbitrary keys."""
    mod = ModuleSchema(
        module_name="test",
        container_image="img:tag",
        arguments={},
        volumes={},
    )
    assert mod.extra == {}
    assert isinstance(mod.extra, dict)


# --- ModuleSchema.from_dict tests ---


def test_from_dict_minimal():
    """from_dict builds a ModuleSchema from a minimal dict."""
    schema = ModuleSchema.from_dict({"module_name": "foo", "container_image": "img:1"})
    assert schema.module_name == "foo"
    assert schema.container_image == "img:1"
    assert schema.arguments == {}
    assert schema.volumes == {}
    assert schema.depends_on is None
    assert schema.command == ""
    assert schema.uses_climate_file is False
    assert schema.extra == {}


def test_from_dict_empty():
    """from_dict handles a completely empty dict with defaults."""
    schema = ModuleSchema.from_dict({})
    assert schema.module_name == ""
    assert schema.container_image == ""
    assert schema.arguments == {}
    assert schema.volumes == {}


def test_from_dict_normalizes_none_arguments():
    """from_dict sets arguments to {} when the YAML value is null/None."""
    schema = ModuleSchema.from_dict({"module_name": "foo", "arguments": None})
    assert schema.arguments == {}


def test_from_dict_normalizes_none_volumes():
    """from_dict sets volumes to {} when the YAML value is null/None."""
    schema = ModuleSchema.from_dict({"module_name": "foo", "volumes": None})
    assert schema.volumes == {}


def test_from_dict_collects_extra_fields():
    """from_dict puts unknown keys into extra."""
    schema = ModuleSchema.from_dict({"module_name": "foo", "per_workflow": True})
    assert schema.extra == {"per_workflow": True}


def test_from_dict_climate_file_required_goes_to_extra():
    """climate_file_required is a known key and is excluded from extra."""
    schema = ModuleSchema.from_dict(
        {"module_name": "foo", "climate_file_required": True}
    )
    assert "climate_file_required" not in schema.extra


def test_from_dict_full():
    """from_dict correctly maps all known fields."""
    data = {
        "module_name": "bamber19-icesheets",
        "container_image": "ghcr.io/org/bamber19:0.2",
        "arguments": {"top_level": [], "options": []},
        "volumes": {"output": {"host_path": "x", "container_path": "/out"}},
        "depends_on": [
            {
                "service": "fair-temperature",
                "condition": "service_completed_successfully",
            }
        ],
        "command": "icesheets",
        "uses_climate_file": True,
        "climate_file_required": True,
        "per_workflow": False,
    }
    schema = ModuleSchema.from_dict(data)
    assert schema.module_name == "bamber19-icesheets"
    assert schema.container_image == "ghcr.io/org/bamber19:0.2"
    assert schema.command == "icesheets"
    assert schema.uses_climate_file is True
    assert schema.depends_on == [
        {"service": "fair-temperature", "condition": "service_completed_successfully"}
    ]
    assert "top_level" in schema.arguments
    assert "output" in schema.volumes
    assert schema.extra == {"per_workflow": False}
    assert "climate_file_required" not in schema.extra
