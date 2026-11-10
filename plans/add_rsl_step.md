# GMSL/RSL Step Split: Implementation Plan

**Base:** this work starts after `add_apptainer_command` is merged, and after the preparatory refactors in `prep_for_add_rsl_step.md`. File paths, line numbers and "current" code below are from branch `add_apptainer_command` at `47f63eb` (2026-10-08) and may drift. All paths are relative to `src/facts_experiment_builder/` unless they start with `tests/` or `docs/`.

## Context

FACTS experiments currently have 4 steps: `climate → sealevel → totaling → extreme_sealevel`. The sealevel step conflates GMSL and RSL contributions. Splitting them enables separate totaled GMSL and RSL outputs.

The GRD fingerprinting module (previously embedded inside individual GMSL modules) is being pulled out as a standalone RSL module — one GRD service per applicable GMSL module. A GMSL module may produce one or multiple output files; the GRD service for that GMSL module receives all of them.

The change has to work for both generators, which share one pipeline (`_make_experiment_plan()` → `_build_module_specs()` → `build_experiment_execution_plan()`) and then render differently:
- **Docker Compose** orders services with `depends_on`.
- **Apptainer** orders services by fixed script stages (`_ApptainerStages` in `application/generate_apptainer.py`, rendered by `templates/apptainer_experiment.sh.j2`). It does not use `depends_on`.

**User-confirmed decisions:**
- GMSL step: multi-module list; some modules ingest climate output, others don't
- RSL step: multi-module list with two entry types (plain string, or parameterized `{module: {gmsl_module: X}}`)
- RSL→GMSL pairing is explicit in the experiment config — same module type can appear multiple times with different `gmsl_module` params
- Totaling: two separate service sets — `facts-total-gmsl-*` and `facts-total-rsl-*`
- Backward compat: shim that treats old `sealevel_modules` as RSL-only with deprecation warning

**New step order:** `climate → gmsl → rsl → totaling-gmsl + totaling-rsl → extreme_sealevel`

---

## New manifest format

The manifest keys are top-level keys in `experiment-config.yaml` (read by `FactsExperiment.from_metadata_dict()` and `_extract_all_module_names_from_manifest()`). The climate key is `climate_module`.

```yaml
climate_module: fair-temperature
gmsl_modules:
  - tlm-sterodynamics
  - bamber19-icesheets
rsl_modules:
  - grd-fingerprinting:
      gmsl_module: tlm-sterodynamics    # one GRD service paired with this GMSL module
  - grd-fingerprinting:
      gmsl_module: bamber19-icesheets   # another GRD service, different pairing
  - kopp14-verticallandmotion           # plain RSL module, no GMSL pairing
framework_modules:
  - facts-total                          # used for both GMSL and RSL totaling
esl_modules:
  - extremesealevel-pointsoverthreshold
```

`_extract_all_module_names_from_manifest()` (`application/generate_compose.py` L68) currently skips non-string list entries (`if isinstance(m, str)`), so dict entries in `rsl_modules` would be dropped silently. It must use `RslModuleInstance.module_name` to find the schema to load (one schema per module, shared by all its instances).

---

## New concept: `RslModuleInstance`

The RSL list supports two entry types. A new dataclass wraps both:

```python
@dataclass
class RslModuleInstance:
    module_name: str               # e.g. "grd-fingerprinting"
    gmsl_module: str | None = None # e.g. "tlm-sterodynamics", or None for plain modules

    @property
    def service_name(self) -> str:
        if self.gmsl_module:
            return f"{self.module_name}-{self.gmsl_module}"
        return self.module_name

    @classmethod
    def from_manifest_entry(cls, entry) -> "RslModuleInstance":
        if isinstance(entry, str):
            return cls(module_name=entry)
        # entry is {module_name: {gmsl_module: X}}
        module_name, params = next(iter(entry.items()))
        return cls(module_name=module_name, gmsl_module=params.get("gmsl_module"))
```

For parameterized instances, `service_name != module_name`. All compose/Apptainer/workflow/totaling code must use `service_name`, not `module_name`, when referencing RSL services.

Precedent: per-workflow facts-total and ESL services already run one module under several service names. `build_module_service_spec()` is called with `module_name=service_name` and a synthetic metadata section stored under `metadata_copy[service_name]` (`application/execution_plan.py`, `_build_facts_total_specs_for_workflows()` and `_build_esl_specs_for_workflows()`). Parameterized RSL instances can follow the same pattern. Note that `ModuleServiceSpec.module_name` is then the service name, and Apptainer uses it as `ApptainerServiceSpec.service_name`.

---

## RSL→GMSL dependency wiring

An RSL module's YAML marks which input receives all GMSL output files via `uses_gmsl_file: true` on the `InputArgSpec` (boolean, not a named output reference):

```yaml
# grd-fingerprinting module YAML
inputs:
  projection_files:
    uses_gmsl_file: true    # builder passes ALL output files from the paired GMSL module here
```

For comparison, the existing climate wiring uses `climate_step_output: str | None` on `InputArgSpec` (`core/module/arg_specs.py` L75, names the climate output consumed) plus a stored `uses_climate_file: bool` field on `ModuleSchema` (`core/module/module_schema.py` L41, read from the module YAML).

The builder:
1. Sees `uses_gmsl_file: true` on an input of a parameterized `RslModuleInstance`
2. Looks up the paired GMSL module (from `RslModuleInstance.gmsl_module`)
3. Enumerates all file outputs from that GMSL module's YAML
4. Wires them to the `uses_gmsl_file` input
5. Orders the RSL service after its paired GMSL service:
   - Compose: `depends_on: {paired_gmsl_service: {condition: service_completed_successfully}}`
   - Apptainer: run the RSL service in a stage after the GMSL stages, and `wait_for_output` on the paired GMSL service's output files (see "Apptainer" below)

Plain RSL modules (no `gmsl_module` param) with `uses_climate_file: true` continue to work exactly as today.

---

## Totaling split

`TotalingStep` class is unchanged. `FactsExperiment` gains two totaling step attributes: `_gmsl_totaling_step` and `_rsl_totaling_step`, both using the same `facts-total` framework module. The shared execution plan produces two distinct service sets from them, used by both generators:
- GMSL totaling: `facts-total-gmsl-<workflow-suffix>`
- RSL totaling: `facts-total-rsl-<workflow-suffix>`

RSL workflows use `RslModuleInstance.service_name` (not `module_name`) when collecting the module list for totaling.

How facts-total services are named and where they write today (all in `core/workflow.py` and `application/execution_plan.py`):
- Service name: `Workflow.facts_total_service_name_for_type()` → `facts-total-<wf>-<output_type>` (`core/workflow.py` L85)
- Output file: `Workflow.total_output_filename_for_type()` → `<wf>_<output_type>_total.nc`, written under the `facts-total` output subdirectory (`_build_facts_total_section_for_workflow()` sets `_output_subdir: "facts-total"`)
- ESL input: `Workflow.total_localsl_path_under_output` → `facts-total/<wf>_local_total.nc`; ESL services are ordered after `wf.facts_total_service_name_for_type("local")` (`_build_esl_specs_for_workflows()`)

All three need a GMSL/RSL distinction (see Risks 3 and 6).

---

## Apptainer

Current stages (`_build_apptainer_stages()`, `application/generate_apptainer.py` L83-145; documented in `docs/generate_apptainer.md` L136-139):

| Stage | Contents | How it runs |
|---|---|---|
| 1 | climate + `standard_specs` with `uses_climate_file: false` | sequential, foreground |
| 2 | `standard_specs` with `uses_climate_file: true` | `wait_for_output` on the climate outputs they need, then sequential |
| 3 | `facts_total_specs` | parallel (`&`), then `wait` on each PID |
| 4 | `esl_specs` + `standalone_esl_specs` | sequential |

Today `standard_specs` is climate + all sealevel modules (`build_experiment_execution_plan()`), so the stage split only knows "climate-dependent or not". After the split it also has to put RSL services after GMSL services.

Proposed stages:

| Stage | Contents |
|---|---|
| 1 | climate + GMSL modules with no climate dependency |
| 2 | GMSL modules that use climate output (`wait_for_output` on climate outputs, as today) |
| 3 | RSL modules. Paired instances `wait_for_output` on their paired GMSL service's outputs; plain RSL modules with `uses_climate_file` wait on climate outputs (already produced by Stage 1) |
| 4 | GMSL and RSL totaling, all in parallel |
| 5 | ESL (after RSL totaling) |

Stages run one after another and only totaling is backgrounded, so stage order alone already guarantees each stage's inputs exist; `wait_for_output` is an extra check, as it is for Stage 2 today.

Changes needed:
- `_ExecutionPlan` (`application/execution_plan.py` L41-70) must tell GMSL and RSL specs apart; `standard_specs` mixes them today. E.g. separate `gmsl_specs`/`rsl_specs` fields, or keep `standard_specs` and add the step name per spec. Both renderers read this.
- `_ApptainerStages` (`application/generate_apptainer.py` L44-54) and `_build_apptainer_stages()`: add the RSL stage and renumber.
- Paired RSL wait files: add a helper like `_get_climate_wait_files()` (L66-80) that returns the paired GMSL service's `ApptainerServiceSpec.host_outputs` values. Every one of the GMSL module's file outputs is passed to the RSL input, so it should wait on all of them.
- `io/write_apptainer.py` `_build_template_context()`: stage keys and `climate_wait_files` / `climate_service_name` are passed per stage by name. The RSL stage needs its own wait files per service (each paired instance waits on a different GMSL service), unlike Stage 2's single merged list.
- `templates/apptainer_experiment.sh.j2`: each stage is a hand-written block with its own header and log line. Option: replace them with one loop over a list of stages (name, mode, services, wait files), so adding a stage is a data change, in the spirit of Refactor A. Otherwise add another block.
- Stage 3 today sets `BINDS` once from `stage3[0].binds` and reuses it for every facts-total service (template L168-172). That only works if every totaling service has identical binds. With GMSL and RSL totaling in the same stage, emit `BINDS` per service as the other stages do.
- `docs/generate_apptainer.md`: update the stage list (L136-139).

Image pulls: the SIF file is named `<service_name>-<image_tag>.sif` (template `pull_image`, `ApptainerServiceSpec` docstring), so each service pulls its own copy of its image. This already happens for facts-total (one SIF per workflow × output type). Each parameterized GRD instance would add another copy of the same image. Consider naming SIFs by image (`image_ref`) instead, so each image is pulled once.

---

## Punch List

### A. New domain type
- [ ] Create `core/module/rsl_module_instance.py` — `RslModuleInstance` dataclass with `service_name` property and `from_manifest_entry()` classmethod

### B. Module YAML / schema layer
- [ ] Add `uses_gmsl_file: bool = False` field to `InputArgSpec` in `core/module/arg_specs.py` (L67). Arg specs use `extra="forbid"` (L36), so module YAMLs that set `uses_gmsl_file` fail validation until this field exists
- [ ] Add `uses_gmsl_file: bool` property to `ModuleSchema` in `core/module/module_schema.py` (derived from whether any input has `uses_gmsl_file: true`). Because it is derived, not stored like `uses_climate_file`, `from_dict()`'s `known_keys` and `to_dict()` need no change

### C. New step classes
- [ ] Create `core/steps/gmsl_step.py` — `GmslStep`, mirrors `SealevelStep` (`core/steps/sealevel_step.py`; multi-module list, accepts `climate_files`)
- [ ] Create `core/steps/rsl_step.py` — `RslStep`; `from_module_schemas()` accepts `climate_files` AND `gmsl_files: dict[str, list[str]]` (paired GMSL module name → all its output file paths); stores `list[RslModuleInstance]`
- [ ] Update `core/steps/__init__.py` — export `GmslStep`, `RslStep`, `RslModuleInstance`
- [ ] Update `StepSet` (from Refactor B) — add `gmsl`, `rsl`, `gmsl_totaling`, `rsl_totaling` fields; remove `sealevel`, `totaling`

### D. Skeleton / CLI
- [ ] Update `ExperimentSkeleton` in `core/experiment/skeleton.py` (L62):
  - Replace `sealevel_modules: list[str]` with `gmsl_modules: list[str]` and `rsl_modules: list[RslModuleInstance]`
  - `all_module_names` (L141) — used to look up schemas (`setup_experiment_cli.py` L263) and validate module names (L282). Schema lookup needs `module_name`; decide whether this property returns module names (one per module) and add a separate property for service names
  - Decide how `supplied_totaled_sealevel_step_data` (and its validation in `from_inputs()`) applies once there are two totaled outputs
- [ ] Update `is_totaling_needed()` — a module-level function in `core/experiment/skeleton.py` (L32) taking the raw `sealevel_step` CLI string, called from `setup_experiment_cli.py` L270. Make it true when either step needs totaling
- [ ] Update `ExperimentSkeleton.from_inputs()` (L80) — parse `--gmsl-step` and `--rsl-step`; RSL input handles both plain strings and `name:gmsl_module=X` parameterized entries; update the totaling domain rules (L117-129)
- [ ] Update `hydrate_experiment()` (L154) — add gmsl→rsl file resolution; return updated `StepSet`
- [ ] Update `setup_experiment.py` `prepare_experiment_setup()` (L43) — new params `gmsl_step`, `rsl_step`
- [ ] Update `cli/setup_experiment_cli.py` — replace `--sealevel-step` (L76) with `--gmsl-step` / `--rsl-step`; update the display/notes that mention `--sealevel-step` (L236)

### E. FactsExperiment domain object
- [ ] Update `FactsExperiment.__init__()` in `core/experiment/experiment.py` (class at L71):
  - Replace `sealevel_step`, `totaling_step` with `gmsl_step`, `rsl_step`, `gmsl_totaling_step`, `rsl_totaling_step`
  - Update `list_all_steps()` (L139) for new order
- [ ] Update `MANIFEST_KEYS` (L34) — add `"gmsl_modules"`, `"rsl_modules"`; remove `"sealevel_modules"` (keep it recognised for the shim, so an old config's `sealevel_modules` key is not mistaken for a module section)
- [ ] `_STRUCTURAL_KEYS` (L48) is built from `MANIFEST_KEYS`; check it still excludes every manifest key
- [ ] Update `from_metadata_dict()` (L175):
  - Parse new keys; RSL list via `RslModuleInstance.from_manifest_entry()`
  - Backward-compat shim: if `sealevel_modules` present and `gmsl_modules`/`rsl_modules` absent, load all as plain `RslModuleInstance` objects + emit deprecation warning

### F. Factories
- [ ] Update `factories.py` `steps_from_metadata()` — read `gmsl_modules`, `rsl_modules`; build `GmslStep`, `RslStep`, two `TotalingStep` instances; return updated `StepSet`

### G. Experiment config writing
- [ ] Update `ExperimentManifest` in `core/experiment/experiment_config.py` (L39) — replace `sealevel_modules: list` with `gmsl_modules: list` and `rsl_modules: list`; RSL entries serialized as mixed string/dict
- [ ] Update `make_included_modules_section()` (L87) — check new keys
- [ ] Update `facts_experiment_to_config()` (L165) — serialize `RslModuleInstance` objects back to manifest format
- [ ] Verify `templates/experiment-config.yaml.j2` — the `included_modules` loop (L40-43) writes `format_value(manifest[module_key])`; confirm it renders dict entries in `rsl_modules`
- [ ] Module sections and `module_schemas` are keyed by module name (`build_module_sections()`, L65). Decide whether parameterized instances get one section per service name (each with its own paired GMSL inputs) or share the module's section

### H. Shared execution pipeline (benefits from Refactor A) — affects Compose and Apptainer
- [ ] Update `_extract_all_module_names_from_manifest()` (`application/generate_compose.py` L68) — read `gmsl_modules`, `rsl_modules`; handle dict RSL entries (currently skipped)
- [ ] Update `_ExperimentPlan.step_module_names` — add `"gmsl"`, `"rsl"` keys populated from new step objects; RSL uses `service_name` not `module_name`
- [ ] Update `_ModuleSpecs.step_modules` in `application/execution_plan.py` — add `"gmsl"` and `"rsl"` entries
- [ ] Update `_build_module_specs()` in `application/generate_compose.py` — RSL loop passes paired GMSL service name (per `RslModuleInstance.gmsl_module`) to `ModuleServiceSpec`; schema lookup by `module_name`, spec keyed by `service_name`
- [ ] Update `_ExecutionPlan` and `build_experiment_execution_plan()` in `application/execution_plan.py` — keep GMSL and RSL specs distinguishable (see "Apptainer"); produce two separate totaling service sets (`facts-total-gmsl-*`, `facts-total-rsl-*`) in `facts_total_specs`
- [ ] Update `_collect_workflow_output_paths_by_type()` — it reads `metadata[mod]["outputs"]` and `schemas.get(mod)` for each name in `wf.module_names`; for RSL workflows these are service names, so it needs the service → module mapping for the schema lookup

### I. Compose rendering
- [ ] Update `ModuleServiceSpec._build_compose_depends_on()` in `core/module/module_service_spec.py` (L497) — add `gmsl_service_name: str | None = None` param; inject GMSL `depends_on` when `uses_gmsl_file=True`
- [ ] `ModuleServiceSpec._get_dependency_names()` (L467) duplicates that logic but has no callers in `src/` or `tests/`; either update it the same way or remove it
- [ ] Update `generate_compose_service()` (L549) and `_build_compose_services()` (`application/generate_compose.py`) to pass the paired GMSL service name

### J. Apptainer rendering
- [ ] Update `_ApptainerStages` and `_build_apptainer_stages()` (`application/generate_apptainer.py`) — new RSL stage; totaling stage holds both GMSL and RSL totaling
- [ ] Add paired-GMSL wait-file helper alongside `_get_climate_wait_files()`
- [ ] Update `io/write_apptainer.py` `_build_template_context()` for the new stage and per-service wait files
- [ ] Update `templates/apptainer_experiment.sh.j2` — new stage (or loop over stages); per-service `BINDS` in the totaling stage
- [ ] Update `docs/generate_apptainer.md` stage list
- [ ] Optional: name SIFs by image so shared images are pulled once

### K. Workflows / totaling prompts
- [ ] Update `cli/setup_experiment_cli.py` call site of `_collect_workflows()` (L271; function in `cli/workflow_prompts.py` L14) — call twice: once for GMSL modules (using module names), once for RSL modules (using `service_name` from each `RslModuleInstance`)
- [ ] Decide how GMSL and RSL workflows are stored: `experiment-config.yaml` has one `workflows:` mapping (name → comma-separated module list) and `Workflow` (`core/workflow.py` L32) has no step field
- [ ] Give GMSL and RSL totaling distinct service names and output filenames (`Workflow.facts_total_service_name_for_type()`, `total_output_filename_for_type()`, `total_localsl_path_under_output`)

### L. Tests
- [ ] Add `tests/unit/test_rsl_module_instance.py` — string and dict parsing, `service_name` generation, round-trip serialization
- [ ] Add `tests/unit/test_gmsl_step.py`, `tests/unit/test_rsl_step.py`
- [ ] Update `tests/unit/test_setup_experiment.py` — replace `sealevel_modules` fixtures with `gmsl_modules` / `rsl_modules` including parameterized entries
- [ ] Update `tests/unit/test_experiment_skeleton.py` — `is_totaling_needed()` tests
- [ ] Update `tests/unit/test_setup_experiment_cli.py` — new CLI options
- [ ] Update `tests/unit/test_workflow_prompts.py` — GMSL and RSL workflow collection
- [ ] Update `tests/unit/test_experiment_config.py` — manifest assertions; serialization of parameterized RSL entries
- [ ] Update `tests/unit/test_generate_compose.py` — parameterized GRD instances produce correct service names and `depends_on`
- [ ] Update `tests/unit/test_execution_plan.py` — two totaling sets; RSL workflow output collection by service name
- [ ] Update `tests/unit/test_generate_apptainer.py` — RSL stage contents and order; paired wait files; `_make_execution_plan()` helper (L168) for any new `_ExecutionPlan` fields
- [ ] Update `tests/unit/test_write_apptainer.py` — `_make_stages()` (L54) and `_make_execution_plan()` (L74) helpers; rendered script has the RSL stage and per-service totaling binds
- [ ] Update `tests/unit/helpers.py` `make_skeleton()` (L43) defaults
- [ ] Update `tests/unit/conftest.py` fixtures

---

## Key Non-Obvious Risks

**1. Parameterized RSL entries are new to the manifest format**
The Jinja2 template's `included_modules` loop iterates manifest values — currently all lists of strings. With mixed string/dict entries in `rsl_modules`, verify the template renders both shapes correctly. Also check CLI display output, and `_extract_all_module_names_from_manifest()`, which skips non-string entries today.

**2. Service name uniqueness and validity for parameterized instances**
`grd-fingerprinting-tlm-sterodynamics` must be a valid Docker Compose service name. Verify combined names stay within Docker Compose limits and contain no invalid characters (dots are not valid in service names). For Apptainer the service name is also used in the SIF filename and in `PID_<NAME>` shell variable names (`_build_apptainer_stages()`: upper-cased, `-` → `_`), so it must be safe in both.

**3. RSL workflows must use `service_name`, not `module_name`**
The workflow system collects module names to order `facts-total` after its inputs (Compose `depends_on`; Apptainer stage order) and to collect their output files (`_collect_workflow_output_paths_by_type()` looks up `metadata[name]` and `schemas.get(name)`). For parameterized RSL instances, `service_name != module_name`. Audit all workflow code paths to ensure `service_name` is used where services are meant and `module_name` where schemas are meant.

**4. ESL ordering and input**
ESL services are built in `_build_esl_specs_for_workflows()` (`application/execution_plan.py`): each takes its input from `wf.total_localsl_path_under_output` and is ordered after `wf.facts_total_service_name_for_type("local")` (Compose `depends_on`; Apptainer: last stage). `ExtremeSealevelStep` has no `depends_on` logic. After the split ESL should read the RSL local total and run after `facts-total-rsl-*` only.

**5. Backward-compat shim produces GMSL-less configs**
Old `sealevel_modules` configs load as RSL-only with a deprecation warning and no GMSL step. This is a valid degenerate state but users must re-generate configs to use the GMSL step.

**6. GMSL and RSL totals can overwrite each other**
Both totaling sets use `facts-total` with `_output_subdir: "facts-total"` and output filename `<wf>_<output_type>_total.nc`. If a GMSL workflow and an RSL workflow share a name, their totals are written to the same file, and in Apptainer they run in parallel in the same stage. Workflow names alone are not enough; the step must be part of the filename or subdirectory.

**7. Apptainer stage assumptions**
The Apptainer script relies on fixed stages, a single merged climate wait list, and one `BINDS` array shared by all totaling services. Each of these needs changing (see "Apptainer"); unlike Compose, a missing ordering change does not fail at generation time, only when the script runs.

---

## Critical Files

| File | Part | Change |
|---|---|---|
| `core/experiment/experiment_plan.py` | Refactor A + Part 2 | `_ExperimentPlan` → step-keyed dict; `"gmsl"`, `"rsl"` keys |
| `application/execution_plan.py` | Refactor A + Part 2 | `_ModuleSpecs` → step-keyed dict; `_ExecutionPlan` GMSL/RSL split; two totaling sets; workflow output collection by service name |
| `application/generate_compose.py` | Refactor A + Part 2 | `_build_module_specs()` (shared with Apptainer); `_extract_all_module_names_from_manifest()`; `_build_compose_services()` |
| `core/steps/factories.py` | Refactor B + Part 2 | `steps_from_metadata()` → `StepSet` |
| `core/experiment/skeleton.py` | Refactor B + Part 2 | `hydrate_experiment()` → `StepSet`; new step fields; `is_totaling_needed()` |
| `core/experiment/experiment.py` | Refactor B + Part 2 | `from_metadata_dict()` call site; manifest keys; backward-compat shim |
| `core/module/rsl_module_instance.py` | Part 2 | **New file** |
| `core/module/arg_specs.py` | Part 2 | Add `uses_gmsl_file: bool` to `InputArgSpec` |
| `core/module/module_schema.py` | Part 2 | Add `uses_gmsl_file` property |
| `core/steps/gmsl_step.py` | Part 2 | **New file** |
| `core/steps/rsl_step.py` | Part 2 | **New file** |
| `core/steps/__init__.py` | Part 2 | Export new types |
| `core/workflow.py` | Part 2 | Distinct GMSL/RSL totaling service names and output filenames |
| `core/experiment/experiment_config.py` | Part 2 | `ExperimentManifest`; RSL serialization |
| `templates/experiment-config.yaml.j2` | Part 2 | Mixed string/dict `rsl_modules` entries |
| `application/setup_experiment.py` | Part 2 | New params |
| `cli/setup_experiment_cli.py` | Part 2 | New CLI options; two `_collect_workflows()` calls |
| `cli/workflow_prompts.py` | Part 2 | GMSL / RSL workflow collection |
| `core/module/module_service_spec.py` | Part 2 | `_build_compose_depends_on()` GMSL support |
| `application/generate_apptainer.py` | Part 2 | `_ApptainerStages`, `_build_apptainer_stages()`; paired GMSL wait files |
| `io/write_apptainer.py` | Part 2 | Template context for new stage |
| `templates/apptainer_experiment.sh.j2` | Part 2 | RSL stage; per-service totaling binds |
| `docs/generate_apptainer.md` | Part 2 | Stage list |

---

## Verification

**After Refactors A + B:** Full test suite passes; `experiment-compose.yaml` and `experiment-apptainer.sh` for existing experiments are byte-identical (see `prep_for_add_rsl_step.md`).

**After Part 2:**
- Generate a compose file with GMSL modules, parameterized GRD RSL entries, and plain RSL entries; confirm:
  - GMSL services run before RSL services
  - Each `grd-fingerprinting-<gmsl-module>` service has `depends_on` only its specific paired GMSL service
  - Plain RSL services with `uses_climate_file` wire to the climate service correctly
  - `facts-total-gmsl-*` and `facts-total-rsl-*` appear as separate service sets, writing to different files
  - ESL services depend on `facts-total-rsl-*` only and read the RSL local total
- Generate an Apptainer script for the same experiment; confirm:
  - GMSL services are in earlier stages than RSL services
  - Each paired GRD service waits for exactly its paired GMSL service's output files
  - Both totaling sets run in the totaling stage, each with its own binds, writing to different files
  - ESL runs last and reads the RSL local total
  - The script runs end-to-end (e.g. in the Lima VM used for `add_apptainer_command`)
- Load an old `sealevel_modules` config; confirm deprecation warning + successful load as RSL-only
- Round-trip test: generate config → reload → regenerate compose and Apptainer script; parameterized RSL entries survive intact
