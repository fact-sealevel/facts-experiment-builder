"""Tests for typed paths (TypedPath, HostPath, ContainerPath) and builder behavior."""

from facts_experiment_builder.core.typed_path import (
    TypedPath,
    HostPath,
    ContainerPath,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
    ModuleContainerImage,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.infra.path_utils import (
    build_module_input_paths,
    build_module_output_paths,
)


def test_typed_path_construction():
    """TypedPath, HostPath, ContainerPath have correct path and kind."""
    tp = TypedPath(path="/mnt/out/a.nc", kind="container")
    assert tp.path == "/mnt/out/a.nc"
    assert tp.kind == "container"

    h = HostPath("/host/path/file.csv")
    assert h.path == "/host/path/file.csv"
    assert h.kind == "host"

    c = ContainerPath("/mnt/out/b.nc")
    assert c.path == "/mnt/out/b.nc"
    assert c.kind == "container"


def test_container_path_list_pass_through():
    """Builder passes through list of ContainerPath unchanged in command args."""
    input_paths = build_module_input_paths(
        module_specific_input_dir="/tmp/mod",
        shared_input_dir="/tmp/gen",
        module_name="test-mod",
    )
    output_paths = build_module_output_paths(
        "/tmp/out", "global", module_name="test-mod"
    )
    components = ModuleServiceSpecComponents(
        module_name="test-mod",
        options={},
        input_paths=input_paths,
        output_paths=output_paths,
        fingerprint_params={},
        inputs={
            "item": [
                ContainerPath("/mnt/total_out/a.nc"),
                ContainerPath("/mnt/total_out/b.nc"),
            ]
        },
        outputs={},
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        metadata={},
        output_container_base=None,
    )
    module_def = ModuleSchema(
        module_name="test-mod",
        container_image="img:tag",
        arguments={
            "top_level": [],
            "options": [],
            "fingerprint_params": [],
            "inputs": [
                {
                    "name": "item",
                    "source": "module_inputs.inputs.item",
                    "mount": {"volume": "input", "container_path": "/mnt/total_in"},
                    "multiple": True,
                }
            ],
            "outputs": {},
        },
        volumes={},
    )
    spec = ModuleServiceSpec(components=components, module_definition=module_def)
    command = spec._build_command_args()
    assert "--item=/mnt/total_out/a.nc" in command
    assert "--item=/mnt/total_out/b.nc" in command


def test_host_path_list_transformed_to_container():
    """Builder transforms list of HostPath to container paths in command args."""
    input_paths = build_module_input_paths(
        module_specific_input_dir="/tmp/module_specific",
        shared_input_dir="/tmp/gen",
        module_name="test-mod",
    )
    output_paths = build_module_output_paths(
        "/tmp/out", "global", module_name="test-mod"
    )
    # Host path under input_dir so relative path is preserved
    components = ModuleServiceSpecComponents(
        module_name="test-mod",
        options={},
        input_paths=input_paths,
        output_paths=output_paths,
        fingerprint_params={},
        inputs={
            "gwd_file": [
                HostPath("/tmp/module_specific/f1.csv"),
                HostPath("/tmp/module_specific/f2.csv"),
            ]
        },
        outputs={},
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        metadata={},
        output_container_base=None,
    )
    module_def = ModuleSchema(
        module_name="test-mod",
        container_image="img:tag",
        arguments={
            "top_level": [],
            "options": [],
            "fingerprint_params": [],
            "inputs": [
                {
                    "name": "gwd-file",
                    "source": "module_inputs.inputs.gwd_file",
                    "mount": {
                        "volume": "input",
                        "container_path": "/mnt/module_specific_in",
                    },
                    "multiple": True,
                }
            ],
            "outputs": {},
        },
        volumes={},
    )
    spec = ModuleServiceSpec(components=components, module_definition=module_def)
    command = spec._build_command_args()
    assert any("/mnt/module_specific_in/f1.csv" in arg for arg in command)
    assert any("/mnt/module_specific_in/f2.csv" in arg for arg in command)


def _make_spec_with_envvar_arg(envvar_name, input_value):
    """Helper: build a ModuleServiceSpec with one input arg that has envvar set."""
    input_paths = build_module_input_paths(
        module_specific_input_dir="/tmp/mod",
        shared_input_dir="/tmp/gen",
        module_name="test-mod",
    )
    output_paths = build_module_output_paths(
        "/tmp/out", "global", module_name="test-mod"
    )
    components = ModuleServiceSpecComponents(
        module_name="test-mod",
        options={},
        input_paths=input_paths,
        output_paths=output_paths,
        fingerprint_params={},
        inputs={"forcing_head_path": input_value} if input_value is not None else {},
        outputs={},
        image=ModuleContainerImage(image_url="img", image_tag="tag"),
        metadata={},
        output_container_base=None,
    )
    module_def = ModuleSchema(
        module_name="test-mod",
        container_image="img:tag",
        arguments={
            "top_level": [],
            "options": [],
            "fingerprint_params": [],
            "inputs": [
                {
                    "name": "forcing-head-path",
                    "source": "module_inputs.inputs.forcing_head_path",
                    "envvar": envvar_name,
                    "optional": True,
                    "mount": {
                        "volume": "module_specific_input",
                        "container_path": "/mnt/module_specific_in",
                    },
                }
            ],
            "outputs": {},
        },
        volumes={},
    )
    return ModuleServiceSpec(components=components, module_definition=module_def)


def test_envvar_arg_excluded_from_command():
    """An input arg with envvar set must not appear in the compose command."""
    spec = _make_spec_with_envvar_arg("EMULANDICE_FORCING_HEAD_PATH", None)
    command = spec._build_command_args()
    assert not any("forcing-head-path" in arg for arg in command)


def test_envvar_arg_with_value_appears_in_environment():
    """When a resolved value exists, it appears in _build_environment() under the declared var name."""
    spec = _make_spec_with_envvar_arg(
        "EMULANDICE_FORCING_HEAD_PATH", HostPath("/tmp/mod/forcing.csv")
    )
    env = spec._build_environment()
    assert "EMULANDICE_FORCING_HEAD_PATH" in env
    assert "forcing.csv" in env["EMULANDICE_FORCING_HEAD_PATH"]


def test_envvar_arg_without_value_not_in_environment():
    """When no value is available, the env var is omitted (container default handles it)."""
    spec = _make_spec_with_envvar_arg("EMULANDICE_FORCING_HEAD_PATH", None)
    env = spec._build_environment()
    assert "EMULANDICE_FORCING_HEAD_PATH" not in env


def test_generate_compose_service_includes_environment():
    """generate_compose_service() propagates environment to the compose dict."""
    spec = _make_spec_with_envvar_arg(
        "EMULANDICE_FORCING_HEAD_PATH", HostPath("/tmp/mod/forcing.csv")
    )
    service = spec.generate_compose_service()
    assert "environment" in service
    assert "EMULANDICE_FORCING_HEAD_PATH" in service["environment"]
