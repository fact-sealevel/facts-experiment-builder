"""Tests for facts_experiment_builder.core.module.facts_module."""

from facts_experiment_builder.core.module.facts_module import FactsModule


def test_facts_module_construction_minimal():
    """FactsModule can be constructed with only required fields."""
    mod = FactsModule(
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


def test_facts_module_construction_with_optionals():
    """FactsModule accepts optional fields with expected defaults overridable."""
    mod = FactsModule(
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


def test_facts_module_post_init_normalizes_none_arguments():
    """__post_init__ sets arguments to {} when passed None (if dataclass allows)."""
    # FactsModule uses a dataclass with arguments: Dict[...]; passing None can happen from YAML load.
    # The type hint doesn't allow None, but __post_init__ guards for it.
    mod = FactsModule(
        module_name="test",
        container_image="img:tag",
        arguments=None,  # type: ignore[arg-type]
        volumes={},
    )
    assert mod.arguments == {}


def test_facts_module_post_init_normalizes_none_volumes():
    """__post_init__ sets volumes to {} when passed None."""
    mod = FactsModule(
        module_name="test",
        container_image="img:tag",
        arguments={},
        volumes=None,  # type: ignore[arg-type]
    )
    assert mod.volumes == {}


def test_facts_module_arguments_structure_preserved():
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
    mod = FactsModule(
        module_name="test",
        container_image="img:tag",
        arguments=arguments,
        volumes={},
    )
    assert mod.arguments == arguments
    assert mod.arguments["top_level"][0]["name"] == "scenario"
    assert len(mod.arguments["inputs"]) == 1
    assert mod.arguments["inputs"][0]["name"] == "climate-data-file"


def test_facts_module_volumes_structure_preserved():
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
    mod = FactsModule(
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


def test_facts_module_extra_default():
    """extra defaults to empty dict and can hold arbitrary keys."""
    mod = FactsModule(
        module_name="test",
        container_image="img:tag",
        arguments={},
        volumes={},
    )
    assert mod.extra == {}
    assert isinstance(mod.extra, dict)
