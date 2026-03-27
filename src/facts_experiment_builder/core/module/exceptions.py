class ModuleYamlMissingSection(Exception):
    def __init__(self, section_name: str):
        self.section_name = section_name

        super().__init__(f"Section '{section_name} not found in module yaml.")
