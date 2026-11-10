# Preparatory changes for adding GMSL/RSL step split

These changes can be made independently of the main split. They reduce the blast radius of Part 2 (`add_rsl_step.md`) and address existing technical debt.

**Base:** this work starts after `add_apptainer_command` is merged. File paths, line numbers and "current" code below are from branch `add_apptainer_command` at `47f63eb` (2026-10-08) and may drift. All paths are relative to `src/facts_experiment_builder/` unless they start with `tests/`.

## Context

`_ExperimentPlan` (`core/experiment/experiment_plan.py`) and `_ModuleSpecs` (`application/execution_plan.py`) hardcode step-specific named fields; `_ModuleSpecs` has a `# TODO do not want these categories to be so rigid in the future` comment. Two functions return plain positional tuples rather than named structures. Fixing these first makes Part 2 mostly additive rather than structural.

Both generators share the same pipeline, so every change here affects Docker Compose **and** Apptainer:

```
_make_experiment_plan()            core/experiment/experiment_plan.py   -> _ExperimentPlan
_build_module_specs()              application/generate_compose.py      -> _ModuleSpecs
build_experiment_execution_plan()  application/execution_plan.py        -> _ExecutionPlan
  ├─ Compose:   _build_compose_services()   application/generate_compose.py
  └─ Apptainer: _build_apptainer_stages()   application/generate_apptainer.py
                render_apptainer_script()   io/write_apptainer.py + templates/apptainer_experiment.sh.j2
```

`generate_apptainer()` imports `_build_module_specs`, `_extract_all_module_names_from_manifest` and `check_module_schemas_present` from `generate_compose.py`. It reads only `plan.workflows` from `_ExperimentPlan` directly (`generate_apptainer.py` L238-241). Neither refactor below changes `_ExecutionPlan`, so the Apptainer stage code and template are not touched by them; they are covered by the before/after verification.

---

## Refactor A — `_ModuleSpecs` and `_ExperimentPlan`: step-keyed dicts

**Problem:** Both dataclasses have hardcoded step-specific named fields. Adding new steps requires adding new named fields everywhere.

**Goal:** Replace the hardcoded step fields with a generic step-keyed structure so adding a new step is a data change, not a structural one.

### `_ExperimentPlan` in `core/experiment/experiment_plan.py`

Current (L45-56):
```python
@dataclass(frozen=True)
class _ExperimentPlan:
    experiment: FactsExperiment
    climate_module_name: str | None  # TODO rename to climate
    sealevel_module_names: list[str]
    framework_module_names: list[str]
    esl_module_names: list[str]
    suppress_output_types: set[str]
    workflows: dict[str, Workflow]
```

Replace the four module-name fields with one step-keyed dict covering every step, climate included (`experiment`, `suppress_output_types` and `workflows` are unchanged):
```python
@dataclass(frozen=True)
class _ExperimentPlan:
    experiment: FactsExperiment
    step_module_names: dict[str, list[str]]
    # e.g. {"climate": [...], "sealevel": [...], "totaling": [...], "extreme_sealevel": [...]}
    suppress_output_types: set[str]
    workflows: dict[str, Workflow]
```

Update `_make_experiment_plan()` (L59-116) to populate `step_module_names` from the experiment's steps.

Consumers of the module-name fields to update:
- `application/generate_compose.py` `_build_module_specs()`: `climate_module_name` (L185-195), `sealevel_module_names` (L203), `framework_module_names` (L215), `esl_module_names` (L229). Shared by Compose and Apptainer.
- `application/execution_plan.py` `_build_facts_total_specs_for_workflows()`: `framework_module_names` (L187).
- `application/execution_plan.py` `build_experiment_execution_plan()`: passes `plan.esl_module_names` to `_build_esl_specs_for_workflows(esl_module_names=...)` (L321). That function's own `esl_module_names` parameter can stay; only the argument changes.

**Why climate goes in the dict too**
- Totaling and ESL are also zero-or-one-module steps, already stored as lists (`[]` when absent). Climate was the only step with its own field and its own "absent" value.
- Despite the `str | None` annotation, `climate_module_name` is never `None`: `_make_experiment_plan()` sets the string `"NONE"` when there is no climate module (L91). With the dict, an absent climate step is `[]`, like any other absent step, and the `"NONE"` sentinel goes away from this layer.
- Climate's special role (other services depend on it; `climate_service_name`) is handled where specs are built (`build_experiment_execution_plan()`, and for Apptainer `_build_apptainer_stages()`, which reads `execution_plan.climate_service_name`), not in the list of names.
- Trade-off: the type no longer says "at most one climate module". Totaling and ESL already lack that. If needed, check it once in `_make_experiment_plan()`.

**Key names:** use the step names (`"climate"`, `"sealevel"`, `"totaling"`, `"extreme_sealevel"`), matching `climate_step`, `sealevel_step`, `totaling_step`, `extreme_sealevel_step` on `FactsExperiment`, rather than the manifest-style `"framework"`/`"esl"`. Insertion order then gives step order. `add_rsl_step.md` adds `"gmsl"`/`"rsl"`; these need to fit the same scheme.

**Problems this fixes in `_build_module_specs()`** (`application/generate_compose.py` L185-199; found by reading the code, not yet reproduced by running an experiment without a climate module). Because Apptainer calls the same function, both apply to `generate-apptainer` too:
1. `schemas[plan.climate_module_name]` runs before the `"NONE"` check. `schemas` is built from `_extract_all_module_names_from_manifest()`, which excludes `"NONE"` (L72), so with no climate module this looks up `schemas["NONE"]` and raises `KeyError`. The property tests hide this by adding `schemas["NONE"] = _minimal_schema("NONE")`.
2. In the `"NONE"` branch, `_validate_climate_file_inputs()` is passed `sealevel_modules`, which is still the empty dict at that point (it is filled by the loop below), so the no-climate check validates nothing. It should get `plan.step_module_names["sealevel"]` and run after the climate branch's name lookup is fixed.

Iterating over `plan.step_module_names["climate"]` like the other steps fixes (1). Fix (2) at the same time, and add a test that runs `_build_module_specs()` without a `"NONE"` schema, plus one that runs `generate_apptainer()` end-to-end on an experiment with no climate module.

**Open question:** whether `_ModuleSpecs` (below) also drops its separate climate field. That is a separate decision: the spec layer does treat climate specially.

### `_ModuleSpecs` in `application/execution_plan.py`

Current (L30-38; docstring omitted):
```python
@dataclass(frozen=True)
class _ModuleSpecs:
    climate_module: ModuleServiceSpec | None
    sealevel_modules: dict[str, ModuleServiceSpec]
    framework_modules: dict[str, ModuleServiceSpec]
    esl_modules: dict[str, ModuleServiceSpec]
    # TODO do not want these categories to be so rigid in the future
```

Replace with:
```python
@dataclass(frozen=True)
class _ModuleSpecs:
    climate_module: ModuleServiceSpec | None
    step_modules: dict[str, dict[str, ModuleServiceSpec]]  # step_name -> {service_name -> spec}
```

Consumers to update:
- `application/generate_compose.py` `_build_module_specs()`: builds `_ModuleSpecs` (L244-249) and checks for an empty result (L251-271: raises unless the steps use supplied data).
- `application/generate_compose.py` `generate_compose()`: checks the same four fields again (L396-404) and, when all are empty, returns `{"services": {}}` without building services. `generate_apptainer()` has no equivalent early return; it always builds stages and renders the script.
- `application/execution_plan.py` `build_experiment_execution_plan()`: reads `specs.climate_module` (L302-307), `specs.sealevel_modules` (L308) and `specs.esl_modules` (L329).

### Files to change
- `core/experiment/experiment_plan.py`: `_ExperimentPlan`, `_make_experiment_plan()`
- `application/execution_plan.py`: `_ModuleSpecs`; `_build_facts_total_specs_for_workflows()`; `build_experiment_execution_plan()`
- `application/generate_compose.py`: `_build_module_specs()`; `generate_compose()` empty-result check (L396)
- `application/generate_apptainer.py`: no change expected (calls the shared functions above)

### Tests to update
- `tests/unit/test_generate_compose_property.py`: the `_make_plan()` helper (L54-67) builds `_ExperimentPlan` with the named fields; remove the `schemas["NONE"] = _minimal_schema("NONE")` workarounds (L137, L156, L175, L225, L255)
- `tests/unit/test_generate_compose.py`: any assertions against named fields on `_ModuleSpecs` or `_ExperimentPlan`
- Not affected: `tests/unit/test_execution_plan.py` L196/L224 pass `esl_module_names=` to `_build_esl_specs_for_workflows()`, whose parameter is unchanged; `tests/unit/test_generate_apptainer.py` and `tests/unit/test_write_apptainer.py` build `_ExecutionPlan` directly (`_make_execution_plan()` helpers), which Refactor A does not change

---

## Refactor B — Named return types for `steps_from_metadata()` and `hydrate_experiment()`

**Problem:** Both functions return positional 4-tuples (`steps_from_metadata()` is annotated `tuple[ClimateStep, SealevelStep, TotalingStep, ExtremeSealevelStep]`; `hydrate_experiment()` just `tuple`). Adding steps requires changing both the return type and every unpacking call site.

**Goal:** Return a named dataclass so the main change adds new fields rather than changing positional unpacking.

### `StepSet` dataclass (new, in `core/steps/factories.py` or `core/steps/__init__.py`)

```python
@dataclass
class StepSet:
    climate: ClimateStep
    sealevel: SealevelStep
    totaling: TotalingStep
    extreme_sealevel: ExtremeSealevelStep
```

- `steps_from_metadata()` (`core/steps/factories.py` L12) returns `StepSet` instead of a 4-tuple
- `hydrate_experiment()` (`core/experiment/skeleton.py` L154) returns `StepSet` instead of a 4-tuple
- Update the two call sites to use attribute access instead of positional unpacking:
  - `FactsExperiment.from_metadata_dict()` (`core/experiment/experiment.py`, call at L254)
  - `experiment_skeleton_to_facts_experiment()` (`core/experiment/skeleton.py` L247, call at L320)
- Export `StepSet` from `core/steps/__init__.py` alongside `steps_from_metadata`

### Files to change
- `core/steps/factories.py`: `steps_from_metadata()` return type
- `core/steps/__init__.py`: export `StepSet`
- `core/experiment/skeleton.py`: `hydrate_experiment()` return type, `experiment_skeleton_to_facts_experiment()` call site
- `core/experiment/experiment.py`: `from_metadata_dict()` call site

### Tests to update
- `tests/unit/test_setup_experiment.py`: unpacks `hydrate_experiment()` positionally in 11 places (L42, L137, L151, L161, L177, L437, L494, L550, L618, L685, L766; L568 is commented out)

---

## Verification (both refactors)

- Full test suite passes.
- Output is byte-identical before and after for real experiments (e.g. `v2_experiments/my_facts_experiment`, `v2_experiments/BC_my_facts_experiment` in the workspace):
  - `generate-compose`: `experiment-compose.yaml`
  - `generate-apptainer`: `experiment-apptainer.sh`. Generate into a scratch copy of the workspace, since generation creates the `output-apptainer` folders.
