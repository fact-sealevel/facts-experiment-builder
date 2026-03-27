from typing import Dict, List
from typing import Protocol

from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)


class ExperimentStep(Protocol):
    """Protocol defining the interfact for experiment step objects.
    Any class that implements is_configured(), module_specs() and to_dict() satisfies the requirements of this protocol.
    """

    def is_configured(self) -> bool: ...
    def module_specs(self) -> List[ModuleExperimentSpec]: ...
    def to_dict(self) -> Dict[str, Dict]: ...
