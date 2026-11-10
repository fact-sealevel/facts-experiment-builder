from facts_experiment_builder.application.execution_plan import _ExecutionPlan
from facts_experiment_builder.core.components.top_level_params import TopLevelParams
from facts_experiment_builder.core.experiment.skeleton import ExperimentSkeleton
from facts_experiment_builder.core.module.arg_specs import (
    ArgumentsSpec,
    InputArgSpec,
    MountSpec,
    OutputFileSpec,
    OutputsSpec,
)
from facts_experiment_builder.core.module.module_inputs_outputs import (
    ModuleInputPaths,
    ModuleOutputPaths,
)
from facts_experiment_builder.core.module.module_schema import (
    ModuleContainerImage,
    ModuleSchema,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
    ModuleServiceSpecComponents,
)


class InMemoryModuleDefinitions:
    def __init__(self, schemas: dict[str, ModuleSchema], version: str = "test"):
        self._schemas = schemas
        self._version = version
        """Helper for tests to create definition objects without using an actual registry """

    def get_schema(self, name: str) -> ModuleSchema:
        return self._schemas[name]

    def module_names(self) -> frozenset[str]:
        return frozenset(self._schemas)

    def version(self) -> str:
        return self._version


# factories to build some test fixtures
def make_schema(
    name="test-module", uses_climate_file=False, arguments=None
) -> ModuleSchema:
    if arguments is None:
        arguments = {
            "inputs": [],
            "options": [],
            "outputs": {"files": [], "other": []},
            "top_level": [],
        }
    return ModuleSchema.from_dict(
        {
            "module_name": name,
            "container_image": "test/image:latest",
            "arguments": arguments,
            "volumes": {},
            "uses_climate_file": uses_climate_file,
        }
    )


def make_skeleton(**overrides) -> ExperimentSkeleton:
    defaults = dict(
        climate_module=None,
        climate_data=None,
        sealevel_modules=[],
        supplied_totaled_sealevel_step_data=None,
        totaling_module=None,
        extremesealevel_module=None,
        module_regions=None,
    )
    return ExperimentSkeleton(**{**defaults, **overrides})


def make_config_raw(**overrides) -> dict:
    """A loaded experiment-config.yaml mapping with every required field set."""
    defaults = {
        "experiment_name": "test_experiment",
        "pipeline-id": "abc123",
        "nsamps": 100,
        "scenario": "ssp585",
        "baseyear": 2005,
        "pyear_start": 2020,
        "pyear_end": 2150,
        "pyear_step": 10,
        "module-specific-input-data": "/in/module",
        "shared-input-data": "/in/shared",
        "compose-output-data-location": "/out/compose",
        "apptainer-output-data-location": "/out/apptainer",
    }
    return {**defaults, **overrides}


def make_service_spec(
    module_name: str,
    uses_climate_file: bool = False,
    output_dir: str = "/output",
    image_url: str = "ghcr.io/fact-sealevel/my-module",
    image_tag: str = "0.1.0",
    climate_step_output: str | None = None,
) -> ModuleServiceSpec:
    inputs = []
    if climate_step_output:
        inputs.append(
            InputArgSpec(
                name="climate-data-file",
                type="str",
                source="module_inputs.inputs.climate_data_file",
                climate_step_output=climate_step_output,
                external_volume=True,
                mount=MountSpec(
                    container_path="/mnt/out", volume="output", transform="filename"
                ),
            )
        )
    schema = ModuleSchema(
        module_name=module_name,
        container_image=f"{image_url}:{image_tag}",
        arguments=ArgumentsSpec(inputs=inputs),
        volumes={},
        uses_climate_file=uses_climate_file,
    )
    components = ModuleServiceSpecComponents(
        module_name=module_name,
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir=f"/input/{module_name}",
            shared_input_dir="/input/shared",
        ),
        output_paths=ModuleOutputPaths(output_dir=output_dir, output_type="global"),
        fingerprint_params={},
        inputs={},
        outputs={},
        image=ModuleContainerImage(image_url=image_url, image_tag=image_tag),
        top_level_params=TopLevelParams(),
    )
    return ModuleServiceSpec(components=components, module_definition=schema)


def make_service_spec_with_outputs(
    module_name: str = "fair-temperature",
    output_root: str = "/out",
    output_dir: str | None = None,
    output_container_base: str | None = None,
    filenames: dict[str, str] | None = None,
    extra_output_volume: str | None = None,
) -> ModuleServiceSpec:
    """ModuleServiceSpec whose outputs live on the shared output volume (mounted at /mnt/out).

    `filenames` maps output arg name -> filename. Components' outputs hold host paths,
    as build_module_service_spec() resolves them.
    """
    filenames = filenames or {
        "output-climate-file": "climate.nc",
        "output-gsat-file": "gsat.nc",
    }
    output_dir = output_dir or f"{output_root}/{module_name}"
    files = [
        OutputFileSpec(
            name=name,
            type="file",
            source=f"module_inputs.outputs.{name.replace('-', '_')}",
            mount=MountSpec(
                container_path="/mnt/out", volume="output", transform="filename"
            ),
            filename=filename,
            output_type="global",
        )
        for name, filename in filenames.items()
    ]
    if extra_output_volume:
        files.append(
            OutputFileSpec(
                name="other-volume-file",
                type="file",
                source="module_inputs.outputs.other_volume_file",
                mount=MountSpec(
                    container_path="/mnt/other", volume=extra_output_volume
                ),
                filename="other.nc",
                output_type="global",
            )
        )
    schema = ModuleSchema(
        module_name=module_name,
        container_image="ghcr.io/fact-sealevel/x:0.1.0",
        arguments=ArgumentsSpec(outputs=OutputsSpec(files=files)),
        volumes={
            "output": {
                "host_path": "module_inputs.output_paths.output_dir",
                "container_path": "/mnt/out",
            }
        },
    )
    outputs = {
        name.replace("-", "_"): f"{output_dir}/{filename}"
        for name, filename in filenames.items()
    }
    if extra_output_volume:
        outputs["other_volume_file"] = f"{output_dir}/other.nc"
    components = ModuleServiceSpecComponents(
        module_name=module_name,
        options={},
        input_paths=ModuleInputPaths(
            input_dir="/input",
            module_specific_input_dir=f"/input/{module_name}",
            shared_input_dir="/input/shared",
        ),
        output_paths=ModuleOutputPaths(output_dir=output_dir, output_type="global"),
        fingerprint_params={},
        inputs={},
        outputs=outputs,
        image=ModuleContainerImage(
            image_url="ghcr.io/fact-sealevel/x", image_tag="0.1.0"
        ),
        top_level_params=TopLevelParams(),
        output_container_base=output_container_base,
    )
    return ModuleServiceSpec(components=components, module_definition=schema)


def make_execution_plan(
    standard_specs: dict | None = None,
    facts_total_specs: dict | None = None,
    esl_specs: dict | None = None,
    climate_service_name: str | None = None,
) -> _ExecutionPlan:
    return _ExecutionPlan(
        standard_specs=standard_specs or {},
        facts_total_specs=facts_total_specs or {},
        esl_specs=esl_specs or {},
        climate_service_name=climate_service_name,
        suppress_output_types=set(),
    )
