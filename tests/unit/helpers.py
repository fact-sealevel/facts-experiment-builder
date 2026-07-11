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
