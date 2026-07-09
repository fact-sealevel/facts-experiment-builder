"""Shared fixtures for unit tests."""

import logging
import pytest
from pathlib import Path
from facts_experiment_builder.core.module.arg_specs import (
    FingerprintParamSpec,
    InputArgSpec,
    MountSpec,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleContainerImage,
    ModuleInputPaths,
    ModuleOutputPaths,
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
)
from facts_experiment_builder.core.registry.module_registry import ModuleRegistry


@pytest.fixture
def experiment_name_correct():
    experiment_name = "experiments/my_test_experiment"
    return experiment_name


@pytest.fixture
def experiment_name_no_parent():
    experiment_name = "my_test_experiment"
    return experiment_name


@pytest.fixture(autouse=True)
def reset_feb_logger():
    """Reset facts_experiment_builder logger state between tests.

    _configure_feb_logging() (called by CLI tests) sets propagate=False on the
    facts_experiment_builder logger. This persists across tests in the same session
    and prevents caplog from capturing log records in later tests.
    """
    yield
    logger = logging.getLogger("facts_experiment_builder")
    logger.propagate = True
    logger.handlers.clear()


@pytest.fixture
def climate_required_true_module_yaml(tmp_path) -> Path:
    """Module YAML file with climate_file_required: true."""
    yaml_path = tmp_path / "test_module_module.yaml"
    yaml_path.write_text("uses_climate_file: true\n")
    return yaml_path


@pytest.fixture
def module_registry() -> ModuleRegistry:
    return ModuleRegistry(
        "/Users/emmamarshall/Desktop/facts_work/facts_v2/facts2-workspace/facts-module-registry"
    )


# @pytest.fixture
# def patched_find_module_yaml_path(climate_required_true_module_yaml: Path):
#     """Patches find_module_yaml_path to return climate_required_module_yaml."""
#     with patch(
#         "facts_experiment_builder.application.generate_compose.find_module_yaml_path",
#         return_value=climate_required_true_module_yaml,
#     ) as mock:
#         yield mock


@pytest.fixture
def mount_spec_out():
    mount_spec = MountSpec(container_path="/mnt/out", volume="output")
    return mount_spec


@pytest.fixture
def mount_spec_shared_in():
    mount_spec = MountSpec(
        container_path="/mnt/shared_in",
        volume="input",
    )
    return mount_spec


@pytest.fixture
def mount_spec_module_specific_in():
    mount_spec = MountSpec(
        container_path="/mnt/module_specific_in",
        volume="input",
    )
    return mount_spec


@pytest.fixture
def climate_data_file_arg_spec():
    """Arg spec for a climate data file input entry of a module schema"""
    climate_data_file = InputArgSpec(
        name="climate-data-file",
        type="str",
        source="module_inputs.inputs.climate_data_file",
        help="Help string",
        climate_step_output="output-climate-file",
        external_volume=True,
        mount=MountSpec(
            container_path="/mnt/out", volume="output", transform="filename"
        ),
    )
    return climate_data_file


@pytest.fixture
def random_module_specific_inputs_arg_spec():
    """Arg spec for arbitrarty input file"""

    input_spec = InputArgSpec(
        name="random-input-file",
        type="str",
        source="module_inputs.inputs.randome_input_file",
        help="help string",
        filename="random_file_name.nc",
        mount=MountSpec(
            container_path="mnt/module_specific_in",
            volume="input",
        ),
    )
    return input_spec


@pytest.fixture
def non_file_input_arg_spec():
    return InputArgSpec(
        name="zosdir",
        type="dir",
        source="module_inputs.inputs.zosdir",
        help="help str",
        mount=MountSpec(volume="input", container_path="/mnt/module_specific_in"),
    )


@pytest.fixture
def fp_module_specific_arg_spec():
    """Fingerprint param that mounts from module-specific storage."""
    return FingerprintParamSpec(
        name="fp-data",
        type="file",
        source="module_inputs.fingerprint_params.fp_data",
        filename="fp_data.nc",
        mount=MountSpec(
            volume="module_specific_in", container_path="/mnt/module_specific_in"
        ),
    )


@pytest.fixture
def fp_shared_arg_spec():
    """Fingerprint param that mounts from shared storage."""
    return FingerprintParamSpec(
        name="fp-shared",
        type="file",
        source="module_inputs.fingerprint_params.fp_shared",
        filename="grd_fingerprints.nc",
        mount=MountSpec(volume="shared_in", container_path="/mnt/shared_in"),
    )


@pytest.fixture
def sealevel_module_schema_that_uses_climate_file():
    return ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={},
        volumes={},
        uses_climate_file=True,
    )


@pytest.fixture
def module_service_spec_components():
    return ModuleServiceSpecComponents(
        module_name="my-module",
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir="/input/my-module",
            shared_input_dir="/input/shared",
        ),
        output_paths=ModuleOutputPaths(
            output_dir="/output",
            output_type="local",
        ),
        fingerprint_params={},
        inputs={},
        outputs={},
        image=ModuleContainerImage(image_url="registry/image", image_tag="latest"),
        metadata={},
    )


@pytest.fixture
def module_service_spec(
    module_service_spec_components, sealevel_module_schema_that_uses_climate_file
):
    return ModuleServiceSpec(
        components=module_service_spec_components,
        module_definition=sealevel_module_schema_that_uses_climate_file,
    )
