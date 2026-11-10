# Refactor Prep for `generate-apptainer`

## The Core Problem

`generate_compose.py` currently does two different jobs in the same functions: **building metadata** (format-agnostic) and **rendering compose services** (compose-specific). These are interleaved rather than separated. That means `generate-apptainer` has to re-implement the metadata-building parts from scratch.

---

## Highest-Value Changes

### 1. Split `_build_per_workflow_services()` and `_create_esl_workflow_services()`

These two functions are the biggest source of would-be duplication. In both, roughly 70% of the code is format-agnostic metadata injection (building the synthetic section, collecting workflow output paths, calling `build_module_service_spec()`), and only the final ~10 lines call `generate_compose_service()` and inject compose-specific `depends_on` syntax.

If each were split into:
- `_build_facts_total_specs_for_workflows()` → returns `list[ModuleServiceSpec]` (format-agnostic)
- `_build_esl_specs_for_workflows()` → returns `list[ModuleServiceSpec]` (format-agnostic)

...then both `generate-compose` and `generate-apptainer` could call these and render independently. This is the highest-leverage change.

### 2. Split `_build_depends_on()` on `ModuleServiceSpec`

Currently this method has two responsibilities:
- Detecting whether a service should depend on another (format-agnostic: checks `uses_climate_file`, maps `"fair"` → actual service name)
- Producing the compose condition dict `{"service_name": {"condition": "service_completed_successfully"}}` (compose-specific)

Separating into:
- `_get_dependency_names() -> list[str]` (shared)
- `_build_compose_depends_on()` (compose-only)

...would make the dependency graph available to apptainer's stage-grouping logic without any reimplementation.

### 3. Introduce an explicit execution plan intermediate representation

Right now, `_build_module_specs()` produces a clean `_ModuleSpecs` dataclass (format-agnostic), but the next call is immediately `_build_compose_services()`, which collapses everything into compose dicts. There is no intermediate format-agnostic "execution plan."

If a step were added between those two — something like `_build_execution_plan(_ModuleSpecs) -> _ExecutionPlan` — both `generate-compose` and `generate-apptainer` could share it and only diverge at the final render. The `_ExecutionPlan` would capture which services are independent, which depend on climate, which are per-workflow parallel, which are ESL — without any format-specific rendering baked in.

---

## What Does Not Need to Change

These are already fully format-agnostic and reusable with zero modification:

| Function / Method | Location | Why reusable |
|---|---|---|
| `_build_command_args()` | `module_service_spec.py` | Returns `list[str]` of CLI flags |
| `_build_volumes()` | `module_service_spec.py` | Returns `list[str]` of `"host:container"` strings |
| `_build_environment()` | `module_service_spec.py` | Returns `dict[str, str]` |
| `_build_module_specs()` | `generate_compose.py` | Returns `_ModuleSpecs` dataclass |
| `build_module_service_spec()` | `module_service_spec.py` | Main factory, no format coupling |
| `_extract_all_module_names_from_manifest()` | `generate_compose.py` | Pure dict extraction |
| `_validate_climate_file_inputs()` | `generate_compose.py` | Pure validation |
| `check_module_schemas_present()` | `generate_compose.py` | Pure validation |
| `_collect_workflow_output_paths_by_type()` | `generate_compose.py` | Pure path aggregation |
| `_build_facts_total_section_for_workflow()` | `generate_compose.py` | Builds metadata dict, not compose dict |
| `_populate_section_with_global/local_outputs()` | `generate_compose.py` | Pure metadata mutation |
| All path-resolution internals | `module_service_spec.py` | No format coupling |

---

## Rough Impact Estimate

| Approach | Apptainer-specific code needed |
|---|---|
| No refactoring (parallel implementation) | ~400 lines |
| With changes 1 + 2 only | ~200 lines |
| With changes 1 + 2 + 3 | ~130 lines |

Changes 1 and 2 are small and low-risk — extracting logic without changing behavior, and existing compose tests would continue to pass. Change 3 is more involved (new intermediate data structure) but makes the architecture significantly cleaner and would make future output formats (Snakemake, Nextflow, etc.) trivial to add.

Whether the refactoring is worth doing before implementing `generate-apptainer` depends on how much you care about long-term maintainability vs. getting something working quickly. The no-refactoring path is faster upfront but creates a maintenance burden where changes to workflow/ESL logic must be made in two places.