from typing import Protocol
from pathlib import Path

# ---------------------- Core imports ----------------------------

from facts_experiment_builder.core.experiment.experiment_config import (
    facts_experiment_to_config,
)
from facts_experiment_builder.core.experiment.experiment import FactsExperiment

# ---------------------- IO imports ----------------------------
from facts_experiment_builder.io.experiment_loader import (
    load_experiment_config,
)
from facts_experiment_builder.io.write_config import write_config_jinja2


# port
class ExperimentRepository(Protocol):
    """Port where experiment config metadata dicts returned from.

    Application code should depend on this instead of load_experiment_config() directly?
    """

    def add(self, experiment: FactsExperiment) -> None: ...
    def get(self, name) -> FactsExperiment: ...


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

    def get(self, config_path: Path) -> FactsExperiment:
        metadata = load_experiment_config(config_path)
        # return FactsExperiment.from_metadata_dict(metadata=metadata)
        return metadata
