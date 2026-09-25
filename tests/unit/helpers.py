from facts_experiment_builder.core.experiment.skeleton import ExperimentSkeleton
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.experiment.skeleton import ExperimentSkeleton


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
