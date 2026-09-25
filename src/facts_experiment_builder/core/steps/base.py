from typing import Protocol

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.module.module_experiment_spec import (
    ModuleExperimentSpec,
)


class ExperimentStep(Protocol):
    """Protocol defining the interfact for experiment step objects.

    Any class that implements is_configured(), module_specs() and to_dict() satisfies
    the requirements of this protocol.
    """

    def is_configured(self) -> bool: ...
    def module_specs(self) -> list[ModuleExperimentSpec]: ...
    def to_dict(self) -> dict[str, dict]: ...
