"""Argument value transforms used when building module commands.

Transforms convert values from experiment metadata into the form expected by
individual modules (e.g. scenario names for ssp-landwaterstorage).
"""

from typing import Any

import yaml

# Config filename for ssp-landwaterstorage scenario name mapping
_SCENARIO_MAPPING_SSP_LWS = "scenario_name_mapping_ssp_landwaterstorage.yaml"


def _load_scenario_mapping_ssp_landwaterstorage() -> dict:
    """Load common -> ssp-landwaterstorage scenario name mapping from config."""
    from facts_experiment_builder.resources import get_module_configs_dir

    path = get_module_configs_dir() / _SCENARIO_MAPPING_SSP_LWS
    if not path.exists():
        return {}
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def scenario_name_ssp_landwaterstorage(common_name: Any) -> str:
    """Convert common scenario name to the form expected by ssp-landwaterstorage.

    Uses the mapping in scenario_name_mapping_ssp_landwaterstorage.yaml.
    If the name is not in the mapping, it is returned unchanged.

    Args:
        common_name: Scenario name from metadata (e.g. "ssp585"). May be a string
            or an object with scenario_name / scenario (will be stringified).

    Returns:
        Scenario string to pass to the ssp-landwaterstorage module.
    """
    if common_name is None:
        return ""
    if hasattr(common_name, "scenario_name"):
        common_name = getattr(common_name, "scenario_name", common_name)
    elif isinstance(common_name, dict):
        common_name = common_name.get(
            "scenario_name", common_name.get("scenario", common_name)
        )
    key = str(common_name).strip() if common_name else ""
    if not key:
        return ""
    mapping = _load_scenario_mapping_ssp_landwaterstorage()
    out = mapping.get(key, key)
    return str(out) if out is not None else key
