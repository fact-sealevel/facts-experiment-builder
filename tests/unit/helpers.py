from facts_experiment_builder.core.experiment.skeleton import ExperimentSkeleton
from facts_experiment_builder.core.module.module_schema import ModuleSchema


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
