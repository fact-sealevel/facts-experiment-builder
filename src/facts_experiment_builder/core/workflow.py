"""Core Workflow type: one workflow (name + sealevel module list) with parsing and
helpers."""

import re
from dataclasses import dataclass

_VALID_WORKFLOW_NAME = re.compile(
    r"^[a-zA-Z0-9_.-]+$"
)  # alphanumeric, no spaces or special chars


@dataclass(frozen=True)
class WorkflowName:
    """Name of a workflow, provided by user in setup-experiment CLI or in experiment
    YAML.

    Used as key in metadata['workflows'].
    """

    name: str

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Workflow name must be a non-empty string")
        if not _VALID_WORKFLOW_NAME.match(self.name):
            raise ValueError(
                "Workflow name must be alphanumeric or one of '-', '_' (no spaces or other special characters)"
            )


@dataclass(frozen=True)
class Workflow:
    """One workflow: name and list of sealevel module names for facts-total.

    Used by setup_new_experiment and generate_compose.
    """

    name: str
    module_names: list[str]

    def __post_init__(self):
        if not isinstance(self.module_names, list):
            raise ValueError(
                f"Workflow module_names must be a list of strings, got: {self.module_names}"
            )
        for m in self.module_names:
            if not isinstance(m, str) or not m.strip():
                raise ValueError(
                    f"Workflow module_names must be non-empty strings, got: {self.module_names}"
                )
        if len(set(self.module_names)) != len(self.module_names):
            raise ValueError(
                f"Workflow module_names must not contain duplicates, got: {self.module_names}"
            )

    @classmethod
    def from_module_list_str(cls, name: str, module_list_str: str) -> "Workflow":
        """Build from workflow name and comma-separated module list string."""
        # Deferred import: avoids a circular import, since core.experiment's
        # __init__ eagerly imports experiment.py, which imports Workflow from here.
        from facts_experiment_builder.core.experiment.module_name_validation import (
            parse_module_list_str,
        )

        modules = parse_module_list_str(module_list_str)
        return cls(name=name, module_names=modules)

    def to_module_list_str(self) -> str:
        """Serialize to comma-separated string for YAML round-trip."""
        return ",".join(self.module_names)

    @classmethod
    def from_dict(cls, name: str, value: str | list[str]) -> "Workflow":
        """Build from metadata value: string (comma-separated) or list of module
        names."""
        if isinstance(value, list):
            module_names = [str(m).strip() for m in value if str(m).strip()]
            return cls(name=name, module_names=module_names)
        return cls.from_module_list_str(name, value if isinstance(value, str) else "")

    def to_dict_value(self) -> str:
        """Value for metadata['workflows'][name] (comma-separated string)."""
        return self.to_module_list_str()

    def facts_total_service_name_for_type(self, output_type: str) -> str:
        """Compose service name for this workflow's facts-total service for a given
        output type (e.g. facts-total-wf1-global)."""
        return f"facts-total-{self.name}-{output_type}"

    @property
    def total_output_filename(self) -> str:
        """Filename for the totaled output (e.g. wf1_total.nc)."""
        return f"{self.name}_total.nc"

    def total_output_filename_for_type(self, output_type: str) -> str:
        """Filename for the totaled output for a given type (e.g. wf1_global_total.nc,
        wf1_local_total.nc)."""
        return f"{self.name}_{output_type}_total.nc"

    @property
    def total_localsl_path_under_output(self) -> str:
        """Path under output root for the local total file (e.g. facts-
        total/wf1_local_total.nc).

        Used by ESL.
        """
        return f"facts-total/{self.total_output_filename_for_type('local')}"


def workflows_from_metadata(metadata: dict) -> dict[str, Workflow]:
    """Build dict[name, Workflow] from metadata['workflows'] (dict[str, str] or
    similar).

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


def workflows_to_metadata(workflows: dict[str, Workflow]) -> dict[str, str]:
    """Serialize Dict[name, Workflow] to Dict[str, str] for YAML (name -> comma-
    separated modules)."""
    return {name: wf.to_dict_value() for name, wf in workflows.items()}
