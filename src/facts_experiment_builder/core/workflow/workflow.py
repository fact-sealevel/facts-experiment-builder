"""Core Workflow type: one workflow (name + sealevel module list) with parsing and helpers."""

from dataclasses import dataclass
from typing import Dict, List, Union


@dataclass(frozen=True)
class Workflow:
    """
    One workflow: name and list of sealevel module names for facts-total.
    Used by setup_new_experiment and generate_compose.
    """

    name: str
    module_names: List[str]

    @classmethod
    def from_module_list_str(cls, name: str, module_list_str: str) -> "Workflow":
        """Build from workflow name and comma-separated module list string."""
        modules = [m.strip() for m in (module_list_str or "").split(",") if m.strip()]
        return cls(name=name, module_names=modules)

    def to_module_list_str(self) -> str:
        """Serialize to comma-separated string for YAML round-trip."""
        return ",".join(self.module_names)

    @classmethod
    def from_dict(cls, name: str, value: Union[str, List[str]]) -> "Workflow":
        """Build from metadata value: string (comma-separated) or list of module names."""
        if isinstance(value, list):
            module_names = [str(m).strip() for m in value if str(m).strip()]
            return cls(name=name, module_names=module_names)
        return cls.from_module_list_str(name, value if isinstance(value, str) else "")

    def to_dict_value(self) -> str:
        """Value for metadata['workflows'][name] (comma-separated string)."""
        return self.to_module_list_str()

    @property
    def facts_total_service_name(self) -> str:
        """Compose service name for this workflow's facts-total service (legacy; one per workflow)."""
        return f"facts-total-{self.name}"

    def facts_total_service_name_for_type(self, output_type: str) -> str:
        """Compose service name for this workflow's facts-total service for a given output type (e.g. facts-total-wf1-global)."""
        return f"facts-total-{self.name}-{output_type}"

    @property
    def total_output_filename(self) -> str:
        """Filename for the totaled output (e.g. wf1_total.nc)."""
        return f"{self.name}_total.nc"

    def total_output_filename_for_type(self, output_type: str) -> str:
        """Filename for the totaled output for a given type (e.g. wf1_global_total.nc, wf1_local_total.nc)."""
        return f"{self.name}_{output_type}_total.nc"

    @property
    def total_localsl_path_under_output(self) -> str:
        """Path under output root for the local total file (e.g. facts-total/wf1_local_total.nc). Used by ESL."""
        return f"facts-total/{self.total_output_filename_for_type('local')}"


def workflows_from_metadata(metadata: Dict) -> Dict[str, Workflow]:
    """
    Build Dict[name, Workflow] from metadata['workflows'] (Dict[str, str] or similar).
    Returns empty dict if workflows key is missing or not a dict.
    """
    raw = metadata.get("workflows")
    if not isinstance(raw, dict):
        return {}
    result = {}
    for wf_name, wf_value in raw.items():
        if not wf_name or not isinstance(wf_name, str):
            continue
        result[wf_name] = Workflow.from_dict(wf_name, wf_value)
    return result


def workflows_to_metadata(workflows: Dict[str, Workflow]) -> Dict[str, str]:
    """
    Serialize Dict[name, Workflow] to Dict[str, str] for YAML (name -> comma-separated modules).
    """
    return {name: wf.to_dict_value() for name, wf in workflows.items()}
