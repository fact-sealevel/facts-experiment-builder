from facts_experiment_builder.core.registry import ModuleRegistry
from facts_experiment_builder.core.experiment.module_name_validation import (
    validate_module_names,
)

import pytest
def test_validate_module_names_passes_for_valid():
    valid_module_names = ["fair-temperature", "ipccar5-icesheets", "ipccar5-glaciers"]
    validate_module_names(valid_module_names, ModuleRegistry.default().list_modules())


def test_validate_module_names_fails_for_invalid():
    invalid_module_names = ["invalid-module-name", "fair-temperature"]
    with pytest.raises(ValueError):
        validate_module_names(
            invalid_module_names,
            ModuleRegistry.default().list_modules(),
        )
