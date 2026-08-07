"""In-memory representation of an experiment (analogous to experiment-config.yaml)."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

# ---------------------- Core imports ----------------------------
from facts_experiment_builder.core.workflow import (
    Workflow,
)
from facts_experiment_builder.core.steps import (
    ClimateStep,
    ExperimentStep,
    SealevelStep,
    TotalingStep,
    ExtremeSealevelStep,
    steps_from_metadata,
)
from facts_experiment_builder.core.components.metadata_bundle import is_metadata_value


