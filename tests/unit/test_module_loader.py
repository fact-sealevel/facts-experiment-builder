import pytest

from facts_experiment_builder.infra.exceptions import ModuleYamlNotFoundError


def load_facts_module_from_yaml_fails_with_false_path(
    yaml_path="/Users/fake/path/to/module/yaml",
):
    assert pytest.raises(ModuleYamlNotFoundError)
