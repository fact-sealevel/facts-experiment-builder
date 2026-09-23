from pathlib import Path
import yaml
from typing import Any

from facts_experiment_builder.core.experiment.experiment_config import (
    facts_experiment_to_config,
)
from facts_experiment_builder.core.experiment.experiment import FactsExperiment

from facts_experiment_builder.io.write_config import (
    write_config_jinja2,
)


def load_experiment_config(metadata_path: Path) -> dict[str, Any]:
    """Load experiment metadata from YAML file."""
    with open(metadata_path) as f:
        return yaml.safe_load(f)


# adapter
class StorageExperimentRepository:
    def add(
        self,
        experiment: FactsExperiment,
        config_path: Path,
        module_registry_version=None,
    ) -> None:
        config = facts_experiment_to_config(experiment, module_registry_version)
        write_config_jinja2(experiment_config=config, config_path=config_path)

    def get(self, config_path: Path) -> dict:
        return load_experiment_config(config_path)
