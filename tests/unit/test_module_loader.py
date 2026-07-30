import pytest

from facts_experiment_builder.io.exceptions import ModuleYamlNotFoundError


def load_module_schema_from_yaml_fails_with_false_path(
    yaml_path="/Users/fake/path/to/module/yaml",
):
    assert pytest.raises(ModuleYamlNotFoundError)
