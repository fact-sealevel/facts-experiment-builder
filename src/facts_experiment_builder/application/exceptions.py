class ModuleRegistryNotFound(Exception):
    def __init__(self, registry_dir: str):
        self.registry_dir = registry_dir

        super().__init__(
            f"Module registry not found at provided location: {registry_dir}."
        )
