from abc import ABC, abstractmethod
from typing import List
from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)


class ExperimentStep(ABC):
    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def to_dict(self) -> dict: ...
    @abstractmethod
    def module_specs(self) -> List[ModuleExperimentSpec]: ...
