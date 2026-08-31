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
from facts_experiment_builder.io.write_config import (
    write_config_jinja2,
    write_module_schemas_yaml,
)


# adapter
class StorageExperimentRepository:
    def add(
        self,
        experiment: FactsExperiment,
        config_path: Path,
        module_schemas_path: Path,
        module_registry_version=None,
    ) -> None:
        config = facts_experiment_to_config(experiment, module_registry_version)
        write_config_jinja2(experiment_config=config, config_path=config_path)
        write_module_schemas_yaml(
            experiment_config=config, module_schemas_path=module_schemas_path
        )

    def get(self, config_path: Path, module_schemas_path: Path) -> dict:
        metadata = load_experiment_config(config_path)
        schemas = load_experiment_config(module_schemas_path)
        for module_name, schema_dict in (schemas or {}).items():
            if isinstance(metadata.get(module_name), dict):
                metadata[module_name]["schema"] = schema_dict
        return metadata
