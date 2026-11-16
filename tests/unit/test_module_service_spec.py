import pytest

from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.module.module_schema import (
    ModuleContainerImage,
    ModuleSchema,
)
from facts_experiment_builder.core.module.module_service_spec import (
    _parse_image,
    ModuleServiceSpecComponents,
    ModuleServiceSpec,
)
from facts_experiment_builder.core.module.source_path import SourcePath
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
)
from tests.unit.helpers import (
    make_schema,
)


def test_input_arg_spec_by_key_returns_correct_spec():
    NotImplementedError


def test_parse_image_string_with_tag():
    result = _parse_image("ghcr.io/example/image:v1.2", "test module")
    assert result == ModuleContainerImage(
        image_url="ghcr.io/example/image", image_tag="v1.2"
    )


def test_parse_image_raises_error_with_no_tag():
    string = "ghcr.io/example/image"
    module_context = "test module"
    with pytest.raises(ValueError):
        _parse_image(image_data=string, module_name_str=module_context)


def test_parse_image_non_string_raises():
    image_dict = {"image_url": "some url", "another key": "another val"}
    module_context = "test module"
    with pytest.raises(ValueError):
        _parse_image(image_data=image_dict, module_name_str=module_context)


@pytest.fixture
def resolve_components():
    return ModuleServiceSpecComponents(
        module_name="module-name",
        options={"seed": 1234},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir="/module_specific_input",
            shared_input_dir="/shared_input_dir",
        ),
        output_paths=ModuleOutputPaths(
            output_dir="output",
            output_type="local",
        ),
        fingerprint_params={"location_file": "location.lst"},
        inputs={"climate_data_file": "fair-temperature/climate.nc"},
        outputs={},
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        output_container_base="output_container",
        top_level_params=TopLevelParams.from_config(
            {
                "experiment_name": "test experiment",
                "pipeline-id": "12345",
                "scenario": "ssp126",
                "nsamps": 50,
                "location-file": "location.lst",
            }
        ),
    )


def test_top_level_params_from_config_reads_kebab_and_snake_keys():
    params = TopLevelParams.from_config({"pipeline-id": "abc", "pyear_end": 2100})
    assert params.pipeline_id == "abc"
    assert params.pyear_end == 2100
    assert params.baseyear is None


def test_resolve_metadata_param(resolve_components):
    source = SourcePath.parse("metadata.pipeline-id")
    assert resolve_components.resolve(source) == "12345"


def test_resolve_metadata_param_missing_from_config_is_none(resolve_components):
    assert resolve_components.resolve(SourcePath.parse("metadata.baseyear")) is None


def test_resolve_module_inputs_section_key(resolve_components):
    source = SourcePath.parse("module_inputs.inputs.climate_data_file")
    assert resolve_components.resolve(source) == "fair-temperature/climate.nc"


def test_resolve_module_inputs_kebab_key_falls_back_to_snake(resolve_components):
    source = SourcePath.parse("module_inputs.inputs.climate-data-file")
    assert resolve_components.resolve(source) == "fair-temperature/climate.nc"


def test_resolve_module_inputs_missing_key_is_none(resolve_components):
    source = SourcePath.parse("module_inputs.options.not_provided")
    assert resolve_components.resolve(source) is None


def test_resolve_module_inputs_paths_attr(resolve_components):
    source = SourcePath.parse("module_inputs.input_paths.shared_input_dir")
    assert resolve_components.resolve(source) == "/shared_input_dir"


def test_resolve_module_name(resolve_components):
    source = SourcePath.parse("module_inputs.module_name")
    assert resolve_components.resolve(source) == "module-name"


@pytest.mark.parametrize(
    "raw, root, attr, key",
    [
        ("metadata.pipeline-id", "metadata", "pipeline_id", None),
        ("metadata.pyear_end", "metadata", "pyear_end", None),
        ("module_inputs.inputs.rcmip-file", "module_inputs", "inputs", "rcmip-file"),
        (
            "module_inputs.fingerprint-params.fp_file",
            "module_inputs",
            "fingerprint_params",
            "fp_file",
        ),
        (
            "module_inputs.fingerprint_params.fp_file",
            "module_inputs",
            "fingerprint_params",
            "fp_file",
        ),
        ("module_inputs.module_name", "module_inputs", "module_name", None),
    ],
)
def test_source_path_parse_valid(raw, root, attr, key):
    source = SourcePath.parse(raw)
    assert (source.root, source.attr, source.key, source.raw) == (root, attr, key, raw)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "metadata",
        "metadata.not_a_param",
        "metadata.pipeline-id.extra",
        "module_inputs.output.x",
        "module_inputs.inputs",
        "module_inputs.inputs.",
        "module_inputs.module_name.extra",
        "module_inpputs.inputs.x",
        "external.some_volume",
    ],
)
def test_source_path_parse_invalid_raises(raw):
    with pytest.raises(ValueError):
        SourcePath.parse(raw)


def test_source_path_leaf_keeps_yaml_spelling():
    assert SourcePath.parse("metadata.location-file").leaf == "location-file"


def test_module_properties_return_correct():
    schema = make_schema()

    input_paths_obj = ModuleInputPaths(
        input_dir="/input",
        module_specific_input_dir="/module_spec_input",
        shared_input_dir="/shared",
    )

    output_paths_obj = ModuleOutputPaths(output_dir="/out", output_type="local")

    container_image = ModuleContainerImage(image_url="test.url", image_tag="latest")
    components = ModuleServiceSpecComponents(
        module_name="test-module",
        options={},
        fingerprint_params={},
        inputs={},
        outputs={},
        input_paths=input_paths_obj,
        output_paths=output_paths_obj,
        image=container_image,
        top_level_params=TopLevelParams(
            pipeline_id="abc123",
            scenario="ssp126",
            baseyear=2005,
            pyear_end=2150,
            pyear_start=2020,
            pyear_step=10,
            nsamps=50,
            location_file="location.lst",
        ),
    )
    module_service_spec = ModuleServiceSpec(
        components=components, module_definition=schema
    )
    assert module_service_spec.module_name == "test-module"
    assert module_service_spec.image == container_image
    assert module_service_spec.input_paths == input_paths_obj
    assert module_service_spec.output_paths == output_paths_obj


@pytest.fixture
def output_spec(tmp_path):
    """A ModuleServiceSpec with one output file on the shared output volume."""
    module_name = "tlm-sterodynamics"
    output_dir = tmp_path / "output" / module_name

    schema = ModuleSchema.from_dict(
        {
            "module_name": module_name,
            "container_image": "test/image:latest",
            "arguments": {
                "outputs": {
                    "files": [
                        {
                            "name": "output-gslr-file",
                            "type": "file",
                            "source": "module_inputs.outputs.output_gslr_file",
                            "filename": "gslr.nc",
                            "output_type": "global",
                            "mount": {
                                "volume": "output",
                                "container_path": "/mnt/out",
                                "transform": "filename",
                            },
                        }
                    ]
                }
            },
            "volumes": {
                "output": {
                    "host_path": "module_inputs.output_paths.output_dir",
                    "container_path": "/mnt/out",
                }
            },
        }
    )

    components = ModuleServiceSpecComponents(
        module_name=module_name,
        options={},
        fingerprint_params={},
        inputs={},
        # Resolved host path, as _resolve_module_outputs_dict produces it
        outputs={"output_gslr_file": str(output_dir / "gslr.nc")},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir="/module_specific_input",
            shared_input_dir="/shared",
        ),
        output_paths=ModuleOutputPaths(
            output_dir=str(output_dir), output_type="global"
        ),
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        output_container_base=None,  # non-facts-total module
        top_level_params=TopLevelParams.from_config({"pipeline-id": "12345"}),
    )
    return ModuleServiceSpec(components=components, module_definition=schema)


def test_output_file_arg_includes_module_subdir(output_spec):
    service = output_spec.generate_compose_service()
    assert "--output-gslr-file=/mnt/out/tlm-sterodynamics/gslr.nc" in service["command"]


def test_output_volume_mounts_shared_output_root(output_spec):
    service = output_spec.generate_compose_service()
    host_output_root = str(output_spec.output_paths.output_dir).rsplit("/", 1)[0]
    assert any(v.startswith(f"{host_output_root}:/mnt/out") for v in service["volumes"])


@pytest.mark.parametrize(
    "command, expected_first",
    [
        ("main", None),  # image default command: no subcommand argument
        ("glaciers", "glaciers"),  # real subcommand is kept first
        ("", None),
    ],
)
def test_command_args_subcommand_shared_by_compose_and_apptainer(
    output_spec, command, expected_first
):
    import dataclasses

    spec = ModuleServiceSpec(
        components=output_spec.components,
        module_definition=dataclasses.replace(
            output_spec.module_definition, command=command
        ),
    )
    compose_command = spec.generate_compose_service()["command"]
    apptainer_args = spec.generate_apptainer_service().args

    assert compose_command == apptainer_args
    assert "main" not in compose_command
    if expected_first is None:
        assert compose_command[0].startswith("--")
    else:
        assert compose_command[0] == expected_first


def test_apptainer_env_matches_compose_environment(output_spec):
    """Inputs declared with `envvar` reach Apptainer as env vars, exactly as Compose
    receives them under `environment:`."""
    import dataclasses

    from facts_experiment_builder.core.module.arg_specs import InputArgSpec, MountSpec

    schema = output_spec.module_definition
    env_input = InputArgSpec(
        name="forcing-head-path",
        type="str",
        source="module_inputs.inputs.forcing_head_path",
        envvar="EMULANDICE_FORCING_HEAD_PATH",
        mount=MountSpec(
            container_path="/mnt/module_specific_in",
            volume="module_specific_input",
        ),
    )
    spec = ModuleServiceSpec(
        components=dataclasses.replace(
            output_spec.components,
            inputs={"forcing_head_path": "forcing"},
        ),
        module_definition=dataclasses.replace(
            schema,
            arguments=schema.arguments.model_copy(
                update={"inputs": [*schema.arguments.inputs, env_input]}
            ),
        ),
    )
    compose_env = spec.generate_compose_service()["environment"]
    apptainer = spec.generate_apptainer_service()
    assert apptainer.env == compose_env
    assert "EMULANDICE_FORCING_HEAD_PATH" in apptainer.env
    # envvar inputs are passed as env, not as CLI args
    assert not any(a.startswith("--forcing-head-path") for a in apptainer.args)
