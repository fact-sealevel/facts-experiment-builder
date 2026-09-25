from facts_experiment_builder.core.experiment.experiment import (
    FactsExperiment,
)
from facts_experiment_builder.core.experiment.experiment_config import (
    facts_experiment_to_config,
)
from facts_experiment_builder.core.steps.climate_step import (
    ClimateStep,
)
from facts_experiment_builder.core.steps.extreme_sealevel_step import (
    ExtremeSealevelStep,
)
from facts_experiment_builder.core.steps.sealevel_step import (
    SealevelStep,
)
from facts_experiment_builder.core.steps.totaling_step import (
    TotalingStep,
)
from tests.unit.helpers import (
    make_schema,
)


def test_experiment_config_includes_module_schemas():
    schema = make_schema(
        "fair-temperature"
    )  # same helper already in test_setup_experiment.py
    exp = FactsExperiment(
        experiment_name="test",
        top_level_params={},
        climate_step=ClimateStep.from_module_schema(schema),
        sealevel_step=SealevelStep(),
        totaling_step=TotalingStep(),
        extreme_sealevel_step=ExtremeSealevelStep(),
        paths={},
        fingerprint_params={},
    )
    config = facts_experiment_to_config(exp, module_registry_version="v1")
    assert (
        config.module_schemas["fair-temperature"]["module_name"] == "fair-temperature"
    )
