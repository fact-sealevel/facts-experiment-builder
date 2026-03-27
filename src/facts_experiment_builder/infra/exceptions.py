class ModuleYamlNotFoundError(Exception):
    def __init__(self, module_name: str, module_yaml_path: str):
        self.module_name = module_name
        self.module_yaml_path = module_yaml_path
        super().__init__(
            f"Module yaml file for '{module_name}' not found at {module_yaml_path}."
        )
