#!/usr/bin/env python3
"""_ExecutionPlan, the backend-neutral module specs for every service in an experiment,
and the helpers that fan facts-total and ESL out per workflow.

prepare_plan.prepare_execution_plan() builds the plan;
execution_graph.build_execution_graph() turns it into an ExecutionGraph.
"""

import logging
from dataclasses import dataclass
from typing import Any

from facts_experiment_builder.core.experiment.experiment_plan import _ExperimentPlan
from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.application.module_service_spec_factory import (
    build_module_service_spec,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    ExperimentDataPaths,
)
from facts_experiment_builder.core.module.module_service_spec import (
    ModuleServiceSpec,
)
from facts_experiment_builder.core.workflow import Workflow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ExecutionPlan:
    """Backend-neutral module specs for every service in an experiment.

    Built by prepare_plan.prepare_execution_plan();
    execution_graph.build_execution_graph() turns it into an ExecutionGraph.

    standard_specs: climate module + all sealevel modules, climate first.

    facts_total_specs: one spec per workflow × output_type. Value is (spec, workflow)
        so renderers can construct depends_on / wait_for from wf.module_names.

    esl_specs: one spec per ESL module × workflow. Value is (spec,
        depends_on_service_name). ESL always runs per workflow because it reads the
        workflow's facts-total output; _make_experiment_plan rejects ESL without
        workflows.

    workflow_names: in experiment-config.yaml order.
    """

    standard_specs: dict[str, ModuleServiceSpec]
    facts_total_specs: dict[str, tuple[ModuleServiceSpec, Workflow]]
    esl_specs: dict[str, tuple[ModuleServiceSpec, str]]
    climate_service_name: str | None
    suppress_output_types: set[str]
    workflow_names: list[str]


def _collect_workflow_output_paths_by_type(
    config: LoadedExperimentConfig,
    wf: Workflow,
    output_type: str,
    schemas: dict[str, "ModuleSchema"],
    *,
    container_prefix: str = "/mnt/total_out",
) -> list[str]:
    """Collect container paths for workflow module outputs that match the given
    output_type and have pass_to_total=True in their module schema.

    For each module in the workflow, reads config.module_sections[mod].outputs; each
    value must be a dict with "value" and "output_type". If a module schema is present
    in `schemas`, only outputs whose OutputFileSpec has pass_to_total=True are included.
    Outputs from modules not found in `schemas` are included for backward compatibility.
    """
    paths: list[str] = []
    prefix = container_prefix.rstrip("/")

    for mod in wf.module_names:
        out_section = config.module_sections.get(mod, {}) or {}
        if not isinstance(out_section, dict):
            continue
        outputs = out_section.get("outputs") or {}
        if not isinstance(outputs, dict):
            continue

        schema = schemas.get(mod)
        pass_to_total_by_name: dict[str, bool] = {}
        if schema is not None:
            pass_to_total_by_name = {
                o.name: o.pass_to_total for o in schema.get_file_outputs()
            }

        for key, v in outputs.items():
            if isinstance(v, dict) and "value" in v:
                p = v.get("value") or ""
                ot = v.get("output_type", "")
            else:
                continue

            if not (p and isinstance(p, str) and ot == output_type):
                continue

            if pass_to_total_by_name and not pass_to_total_by_name.get(key, True):
                logger.info(
                    "%s output '%s': pass_to_total=false, skipping.",
                    mod,
                    key,
                )
                continue

            paths.append(f"{prefix}/{p.strip()}")
    return paths


def _build_facts_total_section_for_workflow(
    wf: Workflow,
    facts_total_image: str,
    output_type: str,
) -> dict[str, Any]:
    """Build the synthetic module section for a facts-total workflow service with empty
    inputs.item and type-specific output-path."""
    return {
        "inputs": {"item": []},
        "outputs": {"output-path": wf.total_output_filename_for_type(output_type)},
        "options": {},
        "fingerprint_params": {},
        "image": facts_total_image,
        "_output_subdir": "facts-total",
        "_output_container_base": "/mnt/total_out/facts-total",
    }


def _populate_section_with_global_outputs(
    section: dict[str, Any],
    config: LoadedExperimentConfig,
    wf: Workflow,
    schemas: dict[str, "ModuleSchema"],
) -> None:
    """Extend section["inputs"]["item"] with container paths for outputs with
    output_type "global"."""
    paths = _collect_workflow_output_paths_by_type(config, wf, "global", schemas)
    section["inputs"]["item"].extend(paths)


def _populate_section_with_local_outputs(
    section: dict[str, Any],
    config: LoadedExperimentConfig,
    wf: Workflow,
    schemas: dict[str, "ModuleSchema"],
) -> None:
    """Extend section["inputs"]["item"] with container paths for outputs with
    output_type "local"."""
    paths = _collect_workflow_output_paths_by_type(config, wf, "local", schemas)
    section["inputs"]["item"].extend(paths)


def _build_facts_total_specs_for_workflows(
    plan: _ExperimentPlan,
    config: LoadedExperimentConfig,
    schemas: dict[str, ModuleSchema],
    data_paths: ExperimentDataPaths,
) -> dict[str, tuple[ModuleServiceSpec, Workflow]]:
    """Build a ModuleServiceSpec for each facts-total workflow × output_type
    combination.

    Returns a dict mapping service_name to (spec, workflow). The workflow is included so
    callers can construct depends_on without re-deriving it.
    """
    specs: dict[str, tuple[ModuleServiceSpec, Workflow]] = {}
    known_module_names = list(schemas.keys())

    facts_total_name = next(
        (m for m in plan.framework_module_names if schemas[m].per_workflow),
        "facts-total",
    )
    facts_total_schema = schemas[facts_total_name]
    facts_total_container_image = facts_total_schema.container_image

    for wf_name, wf in plan.workflows.items():
        for output_type in facts_total_schema.output_types:
            if output_type == "local" and plan.experiment.projection_scale == "global":
                logger.info(
                    "Skipping local facts-total for %s (projection_scale=global)",
                    wf_name,
                )
                continue
            section = _build_facts_total_section_for_workflow(
                wf, facts_total_container_image, output_type
            )
            if output_type == "global":
                _populate_section_with_global_outputs(
                    section, config, wf, schemas=schemas
                )
            else:
                _populate_section_with_local_outputs(
                    section, config, wf, schemas=schemas
                )
            service_name = wf.facts_total_service_name_for_type(output_type)
            spec = build_module_service_spec(
                section,
                config=config,
                module_name=service_name,
                known_module_names=known_module_names,
                module_definition=facts_total_schema,
                data_paths=data_paths,
            )
            specs[service_name] = (spec, wf)
    return specs


def _build_esl_specs_for_workflows(
    esl_module_names: list[str],
    workflows: dict[str, Workflow],
    config: LoadedExperimentConfig,
    projection_scale: str | None,
    schemas: dict[str, ModuleSchema],
    data_paths: ExperimentDataPaths,
) -> dict[str, tuple[ModuleServiceSpec, str]]:
    """Build a ModuleServiceSpec for each ESL module × workflow combination.

    Returns a dict mapping service_name to (spec, depends_on_service_name). The
    depends_on_service_name is the facts-total-local service that must complete before
    this ESL service runs.
    """
    specs: dict[str, tuple[ModuleServiceSpec, str]] = {}
    known_module_names = list(schemas.keys())

    if not esl_module_names:
        return specs
    if projection_scale == "global":
        logger.info("Skipping per-workflow ESL services (projection_scale=global)")
        return specs

    for module_name in esl_module_names:
        schema = schemas[module_name]
        total_localsl_keys = schema.get_output_volume_input_keys()
        if not total_localsl_keys:
            raise ValueError(
                f"ESL module '{module_name}' has no input mounted from the shared "
                "output volume, so it cannot receive the totaling step's output. "
                "Check the module's YAML for an `inputs` entry with `mount.volume: output`."
            )

        base_section = config.module_sections.get(module_name) or {}
        if not isinstance(base_section, dict):
            base_section = {}
        for _wf_name, wf in workflows.items():
            service_name = f"{module_name}-{wf.name}"
            base_inputs = dict(base_section.get("inputs") or {})
            for key in total_localsl_keys:
                base_inputs[key] = wf.total_localsl_path_under_output
            base_outputs = base_section.get("outputs") or {}
            # No YAML section exists for this per-workflow service: clone the
            # module's real section, repointing its totaling inputs at this
            # workflow's total and its output at the service's output root.
            synthetic_section = {
                **base_section,
                "inputs": base_inputs,
                "outputs": {**base_outputs, "output-dir": "."},
            }
            esl_spec = build_module_service_spec(
                synthetic_section,
                config=config,
                module_name=service_name,
                known_module_names=known_module_names,
                module_definition=schema,
                data_paths=data_paths,
            )
            depends_on_service = wf.facts_total_service_name_for_type("local")
            specs[service_name] = (esl_spec, depends_on_service)
    return specs
