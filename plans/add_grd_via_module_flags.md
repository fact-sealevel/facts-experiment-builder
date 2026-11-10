# GRD fingerprinting via module YAML flags (no new steps)

Alternative to `add_rsl_step.md`. Same goal: the GRD fingerprinting that is currently built into individual sea-level modules becomes a standalone `grd-fingerprinting` module. FEB runs one GRD service per sea-level module that needs it, and passes that module's outputs to it. This plan does it with flags in module YAMLs and the existing step structure (`climate → sealevel → totaling → extreme_sealevel`), instead of splitting the sea-level step into GMSL and RSL steps.

**Base:** this work starts after `add_apptainer_command` is merged. File paths and line numbers are from branch `add_apptainer_command` at `47f63eb` (2026-10-08) and may drift. Paths are relative to `src/facts_experiment_builder/` unless they start with `tests/` or `docs/`.

**Status:** proposal. The flag names below are placeholders. Decisions still open are listed under "Open questions".

---

## Why no new steps are needed

What the GMSL/RSL split was meant to deliver, and what already exists:

| Need | Already in FEB | Added by this plan |
|---|---|---|
| Separate GMSL and RSL totals | Every module output is tagged `output_type: global` or `local`. facts-total runs once per workflow × output type (`facts-total-<wf>-global`, `facts-total-<wf>-local`), and `_collect_workflow_output_paths_by_type()` (`application/execution_plan.py` L73) picks outputs by that tag. The global total is the GMSL total; the local total is the RSL total. | Local totals use a module's GRD outputs instead of its own local outputs (see "Totaling"). |
| Plain RSL modules (VLM, GIA) | Already sea-level modules with only `local` outputs (`kopp14-`, `nzinsargps-`, `oelsmann24-verticallandmotion`, `caron18-gia` in the registry). | Nothing. |
| One GRD service per GMSL module | facts-total sets `per_workflow: true`; `_build_module_specs()` skips it (`application/generate_compose.py` L216) and `_build_facts_total_specs_for_workflows()` (L171) builds one service per workflow from a synthetic config section. | The same fan-out, per paired module instead of per workflow. |
| Passing module outputs to GRD | ESL reads facts-total's output through an input mounted on the shared output volume (`ModuleSchema.get_output_volume_input_keys()`, `core/module/module_schema.py` L97; used in `_build_esl_specs_for_workflows()`, L226). facts-total's `item` input (`multiple: true`) already takes a list of container paths. | An input flag on the GRD YAML ("receives the paired module's GRD files") and a per-output flag on the paired module saying which files those are. |
| Ordering | Compose: ESL services get a generated `depends_on` on one facts-total service. Apptainer: fixed script stages. | Compose: `depends_on` the paired module. Apptainer: one new stage. |

What is avoided compared with `add_rsl_step.md`: new manifest keys, `--gmsl-step`/`--rsl-step`, new step classes, `StepSet` changes, the backward-compatibility shim, mixed string/dict manifest entries, a second set of workflows, and GMSL/RSL totals overwriting each other. The preparatory Refactors A and B in `prep_for_add_rsl_step.md` are not needed for this plan. The two climate-module bugs described there (`KeyError` with no climate module; empty climate-file check) should still be fixed separately.

---

## GRD module interface

From the prototype at `fact-sealevel/grd-fingerprinting`, branch `marimo_version` (read 2026-10-08; "small details will change, but this is the rough shape"). CLI (`src/grd_fingerprinting/cli.py`):

| CLI option | What it is | FEB argument section |
|---|---|---|
| `--projection-files` (`multiple=True`, required) | GMSL projection netCDFs to convert to RSL | `inputs`, `multiple: true`, on the shared output volume; filled by FEB from the paired module's outputs |
| `--grd-fingerprint-map-file` (required) | YAML mapping each `source_region` to a fingerprint netCDF | `inputs`, module-specific input data (GRD's own data) |
| `--fingerprint-dir` (required) | Folder holding the fingerprint netCDFs named in the map | `fingerprint_params`, as converted modules declare it today |
| `--location-file` (required) | Locations to project to | `top_level` (`metadata.location-file`), as converted modules declare it today |
| `--scenario`, `--baseyear` (required) | Experiment scenario and base year | `top_level` |
| `--chunksize` | Locations processed at once | `options` |
| `--output-lslr-file` (required) | Output RSL netCDF | `outputs.files`, `output_type: local` |

What the interface means for FEB:
- **All of a module's files go in one run**, as repeated `--projection-files=<file>` flags. FEB already renders a list-valued `multiple: true` input that way (`_format_arg()`, `core/module/module_service_spec.py`). So one GRD service per paired module fits.
- **Fingerprint choice is in the data, not in FEB.** Each projection file carries a `source_region` coordinate (e.g. `AIS.WAIS1`, `GIS.ALL`, `GLA.RGI01`), which GRD looks up in the map file. FEB does not need per-module GRD settings.
- **Input file format.** Each projection file needs a `sea_level_change` variable over `year`/`sample`/`budget_term`/`source_region`. Converted modules' global outputs must be written in this format, with `source_region` values that are keys in the map file. That is a module container change, not an FEB change.
- **GRD adds up every file it gets, per `budget_term`.** Contributions from all source regions with the same `budget_term` are summed into one result. So the files passed must be the non-overlapping regional parts, never an aggregate together with its parts. Several modules write both: `ipccar5-icesheets` writes `global-ais-output` (`pass_to_total: true`) and its parts `global-wais-output` / `global-eais-output` (`pass_to_total: false`); `bamber19-icesheets` writes `AIS-gslr`, `EAIS-gslr` and `WAIS-gslr` (it sets no `pass_to_total`). Passing "all global outputs" would count Antarctica twice. Each module must mark which outputs go to GRD (see "Module YAML flags").
- **One output file per run.** The prototype writes one file per `budget_term`, all to the same `--output-lslr-file` path, so if one run's files span two `budget_term`s the last one written wins. Either each converted module's GRD files share one `budget_term`, or GRD writes one file per `budget_term` (then FEB needs to know the output filenames). To raise with the GRD module.

---

## Module YAML flags

### On a sea-level module that needs GRD (the "paired" module)

```yaml
# e.g. ipccar5-icesheets module YAML
grd_fingerprinting:
  module: grd-fingerprinting     # module to run on this module's outputs

arguments:
  outputs:
    files:
      - name: "global-ais-output-file"
        output_type: "global"
        pass_to_total: true      # AIS total goes to the global total...
        pass_to_grd: false         # ...but not to GRD (its parts do)
      - name: "global-wais-output-file"
        output_type: "global"
        pass_to_total: false
        pass_to_grd: true          # regional part: fingerprinted by GRD
      - name: "global-eais-output-file"
        output_type: "global"
        pass_to_total: false
        pass_to_grd: true
      - name: "global-gis-output-file"
        output_type: "global"
        pass_to_total: true
        pass_to_grd: true
```

- Pairing is declared here, once per module type (decision (a) from the discussion). Every experiment that uses this module gets a GRD service for it.
- `pass_to_grd` on each output says which files GRD receives, the way `pass_to_total` says which go to facts-total. The two are separate flags because they often differ: the global total wants the aggregate (AIS), GRD wants its regional parts (WAIS, EAIS).
- Default `false`, unlike `pass_to_total` (default `true`): sending a file to GRD by mistake double-counts, so it is opt-in per output. A module with `grd_fingerprinting` but no `pass_to_grd: true` output is an error.
- The module's YAML no longer lists `local` outputs or fingerprint arguments (`fingerprint-dir`, `location-file`) once its container stops doing GRD itself; GRD declares them instead. That is a registry and container change, not an FEB change.
- `ModuleSchema.from_dict()` puts unknown top-level keys into `extra` (`known_keys`, L139-151), so `grd_fingerprinting` can be added to registry YAMLs before FEB reads it. `pass_to_grd` cannot: it is on an output spec, and arg specs use `extra="forbid"`, so FEB must add the field to `OutputFileSpec` (`core/module/arg_specs.py`) first.

### On the GRD module

```yaml
module_name: grd-fingerprinting
per_paired_module: true          # never run on its own; one service per module that requests it
arguments:
  top_level:
    # location-file, scenario, baseyear (as other modules declare them)
  fingerprint_params:
    # fingerprint-dir (as converted modules declare it today)
  options:
    - name: "chunksize"
      ...
  inputs:
    - name: "projection-files"
      type: "file"
      multiple: true
      paired_module_outputs: true    # FEB fills this with the paired module's pass_to_grd outputs
      mount:
        volume: "output"
        container_path: "/mnt/out"
    - name: "grd-fingerprint-map-file"
      ...                            # module-specific input data
  outputs:
    files:
      - name: "output-lslr-file"
        filename: "lslr.nc"
        output_type: "local"
```

- `per_paired_module: true` works like `per_workflow: true`: `_build_module_specs()` skips the module, and the execution plan builds one service per paired module.
- `paired_module_outputs` is a new field on `InputArgSpec` (`core/module/arg_specs.py` L67). Arg specs use `extra="forbid"`, so FEB must add the field before a GRD YAML that uses it can be loaded.
- Outputs on the shared output volume are addressed as `<container_path>/<module>/<filename>` (the volume mounts the output root). The paired module's output values in `experiment-config.yaml` are already `<module>/<filename>` (e.g. `tlm-sterodynamics/gslr.nc`), so the GRD input values are `/mnt/out/<paired>/<filename>`, the same pattern `_collect_workflow_output_paths_by_type()` uses with its `container_prefix`. GRD reads the paired module's files and writes its own on the same volume.

---

## How GRD enters an experiment

`grd-fingerprinting` is listed in `sealevel_modules` like any other sea-level module, the same way facts-total is listed in `framework_modules` although it only runs per workflow. That gives it a config section and a frozen schema in `module_schemas` with no new manifest key.

Recommended: setup adds it automatically (open question 1).
- At setup, after loading schemas for the chosen modules (`cli/setup_experiment_cli.py` L263-267), collect the `grd_fingerprinting.module` values and add those modules to the sea-level list if they are not already there.
- Add them after workflows are collected (L270-275), so GRD never appears as a choice in the workflow prompts.
- Add them whatever `projection_scale` is, so changing `global` → `local` later by editing the config works (the GRD schema is already in `module_schemas`).

---

## Service names and output folders

- Service name: `<grd-module>-<paired-module>`, e.g. `grd-fingerprinting-bamber19-icesheets`.
- Output folder: `resolve_module_paths()` (`core/module/module_service_path_resolution.py` L373) puts each service's outputs in `<output root>/<service name>` (only `facts-total-*` services are special-cased, L411). So each GRD service gets its own folder with no change, and the same output filenames can be reused across GRD services.
- Module-specific input folder: taken from the module definition's `input_dir_name` (L403), not the service name, so all GRD services share `grd-fingerprinting`'s input data. This is how per-workflow ESL services already work.
- Synthetic config section per GRD service, built at generation like facts-total's and ESL's (`metadata_copy[service_name] = section`): the GRD module's own section (so `chunksize`, the map file etc. are set once for all GRD services), with `projection-files` filled with the paired module's `pass_to_grd` outputs and output values `<service name>/<filename>`.

---

## Totaling

- **Global totals:** unchanged. They take each workflow module's `global` outputs.
- **Local totals:** for each module in the workflow, take the local outputs of its GRD service if it has one, otherwise the module's own local outputs. Modules not yet converted to GRD keep working, so registry modules can move to GRD one at a time.
- Workflows in `experiment-config.yaml` still list sea-level modules only; users never list GRD services.
- `_collect_workflow_output_paths_by_type()` reads `metadata[mod]["outputs"]` and `schemas.get(mod)` for each workflow module. It needs the synthetic GRD sections and a map from paired module to GRD service. Simplest: build the GRD synthetic sections first in `build_experiment_execution_plan()` (L288) and pass the extended metadata and the map to the facts-total builder.
- Output filenames are unchanged (`<wf>_global_total.nc`, `<wf>_local_total.nc`), so ESL needs no change: it still reads the local total.
- `pass_to_total` continues to apply, now to GRD outputs too.

---

## `projection_scale`

With `projection_scale: global`, GRD services are not created: all their outputs are `local`, and local outputs are suppressed. Add this next to the existing skips for local facts-total (`execution_plan.py`, in `_build_facts_total_specs_for_workflows()`) and ESL (`_build_esl_specs_for_workflows()`, `build_experiment_execution_plan()`).

This turns off all GRD services at once. Turning GRD off for one module but not others is not supported, and probably not wanted: that module would then contribute nothing to the local total.

---

## Execution plan

Add to `_ExecutionPlan` (`application/execution_plan.py` L42):
```python
grd_specs: dict[str, tuple[ModuleServiceSpec, str]]  # service name -> (spec, paired service name)
```
Same shape as `esl_specs`. Built in `build_experiment_execution_plan()` from the sea-level specs whose schema declares `grd_fingerprinting`, unless `projection_scale` is `global`.

## Compose rendering

In `_build_compose_services()` (`application/generate_compose.py` L275):
- Each GRD service: `depends_on: {<paired service>: {condition: service_completed_successfully}}`, as ESL services do.
- facts-total local services (L299-306): `depends_on` also lists the GRD service of each workflow module that has one. Global services are unchanged.

## Apptainer rendering

New stage between the current Stage 2 and Stage 3:

| Stage | Contents |
|---|---|
| 1 | climate + sea-level modules with no climate dependency (unchanged) |
| 2 | sea-level modules that use climate output (unchanged) |
| **3 (new)** | GRD services, sequential; each `wait_for_output` on its paired module's `pass_to_grd` files |
| 4 | facts-total (was 3) |
| 5 | ESL (was 4) |

- `_ApptainerStages` and `_build_apptainer_stages()` (`application/generate_apptainer.py` L44-54, L83-145): add the GRD stage from `execution_plan.grd_specs`.
- Wait files: the paired module's `ApptainerServiceSpec.host_outputs` (all outputs, host paths), filtered to its `pass_to_grd` outputs; a helper next to `_get_climate_wait_files()` (L66-80). Pass them as `wait_for_files` (already a field on `ApptainerServiceSpec`).
- Template (`templates/apptainer_experiment.sh.j2`): the Stage 2 block uses one merged `climate_wait_files` list. The GRD stage needs each service's own `spec.wait_for_files`, emitted before that service. Update stage numbers and log lines; `io/write_apptainer.py` `_build_template_context()` passes the new stage.
- Stages run one after another, so stage order already guarantees the paired outputs exist; `wait_for_output` is an extra check, as in Stage 2.
- SIF files are named `<service_name>-<image_tag>.sif`, so each GRD service pulls its own copy of the same image (facts-total already does this per workflow × output type). Optional: name SIFs by image so each image is pulled once.
- `docs/generate_apptainer.md`: update the stage list.

---

## Validation (at generation, with clear errors)

- A module declares `grd_fingerprinting.module: X` but X is not in the experiment (only possible if setup does not add it automatically, or the config was edited).
- X's schema does not set `per_paired_module: true`, or has no input with `paired_module_outputs`.
- The paired module has no output with `pass_to_grd: true`, or a `pass_to_grd` output is not `global`.
- A `per_paired_module` module is in the experiment but no module requests it: warn, nothing to run.
- Generated service names are valid Docker Compose service names and safe in Apptainer `PID_` variable names.

---

## Punch list

### A. Schema
- [ ] `core/module/module_schema.py`: `per_paired_module: bool` and a typed `grd_fingerprinting` field (module name); add both to `known_keys`, `from_dict()`, `to_dict()`
- [ ] `core/module/arg_specs.py`: `paired_module_outputs: bool = False` on `InputArgSpec`; `pass_to_grd: bool = False` on `OutputFileSpec`

### B. Setup
- [ ] `cli/setup_experiment_cli.py`: add requested GRD modules to the sea-level list after workflow collection (if open question 1 is "automatic")
- [ ] Check `hydrate_experiment()` / `SealevelStep` write a normal config section and frozen schema for the GRD module
- [ ] `application/check_data.py`: confirm GRD's input data is checked like any sea-level module's

### C. Shared execution pipeline (Compose and Apptainer)
- [ ] `application/generate_compose.py` `_build_module_specs()`: skip `per_paired_module` modules, as `per_workflow` ones are skipped
- [ ] `application/execution_plan.py`: build GRD synthetic sections and specs; `_ExecutionPlan.grd_specs`; skip when `projection_scale` is `global`
- [ ] `application/execution_plan.py`: local totals use GRD outputs for paired modules

### D. Compose
- [ ] `_build_compose_services()`: GRD `depends_on`; facts-total local `depends_on` includes GRD services

### E. Apptainer
- [ ] `_ApptainerStages`, `_build_apptainer_stages()`: GRD stage, renumber
- [ ] Paired-output wait-file helper
- [ ] `io/write_apptainer.py`, `templates/apptainer_experiment.sh.j2`: GRD stage with per-service waits
- [ ] `docs/generate_apptainer.md`: stage list

### F. Tests
- [ ] `tests/unit/test_module_schema.py`, `tests/unit/test_arg_specs.py`: new fields load and round-trip
- [ ] `tests/unit/test_execution_plan.py`: one GRD spec per paired module; `projection-files` gets exactly the paired module's `pass_to_grd` outputs (an aggregate like AIS with `pass_to_grd: false` is left out); local totals use GRD outputs, global totals unchanged; no GRD specs when `projection_scale` is `global`; unconverted modules keep their own local outputs
- [ ] `tests/unit/test_generate_compose.py`: GRD `depends_on`; facts-total local `depends_on`
- [ ] `tests/unit/test_generate_apptainer.py`, `tests/unit/test_write_apptainer.py`: GRD stage order and per-service waits; `_make_execution_plan()` / `_make_stages()` helpers for the new fields
- [ ] Setup tests: GRD added automatically and not offered in workflow prompts
- [ ] Validation errors above

### G. Registry (separate repo: facts-module-registry)
- [ ] New `grd-fingerprinting` module YAML (arguments as in "GRD module interface")
- [ ] Per converted module: add `grd_fingerprinting`; mark `pass_to_grd` outputs; remove `local` outputs and fingerprint arguments (with the matching container release, whose GRD files are in GRD's input format with `source_region` values from the map file)

---

## Open questions

1. **How GRD enters the experiment:** added automatically at setup (recommended above), or listed by the user in `--sealevel-step`? If listed by the user, it must be kept out of the workflow prompts.
2. **Config-level override of the pairing:** this plan declares pairing only in module YAMLs. Is a config override needed (e.g. pair a module that does not declare GRD, or use a different GRD module or version for one module)? `projection_scale: global` already covers turning GRD off entirely.
3. **GRD output files:** the prototype writes one file per `budget_term`, all to the same path (see "GRD module interface"). Either each converted module's `pass_to_grd` files share one `budget_term`, or GRD writes one file per `budget_term` and FEB is told their names. To settle with the GRD module.
4. **Flag names:** `pass_to_grd` (agreed, matches `pass_to_total`). `grd_fingerprinting`, `per_paired_module` and `paired_module_outputs` are placeholders. A generic name (e.g. a "post-processor" concept) would allow other per-module post-processing later.
5. **Check existing totals (separate from this plan):** `bamber19-icesheets` writes `AIS-gslr`, `EAIS-gslr` and `WAIS-gslr` and sets no `pass_to_total`, so all three go to facts-total (default `true`). If AIS is EAIS + WAIS, Antarctica is already counted twice in its totals; `ipccar5-icesheets` avoids this with `pass_to_total: false` on its parts. Not verified against the module's actual outputs.

Resolved by the GRD interface (`marimo_version`):
- Per-module GRD settings are not needed: fingerprints are chosen from each file's `source_region` via GRD's map file.
- GRD takes all of a module's files in one run (repeated `--projection-files`).
- `fingerprint-dir` and `location-file` are GRD arguments; converted modules drop them.

---

## Verification

- Existing experiments (no module declares GRD): `experiment-compose.yaml` and `experiment-apptainer.sh` byte-identical before and after.
- Experiment with converted modules, unconverted modules and a VLM module:
  - one `grd-fingerprinting-<module>` service per converted module, receiving exactly that module's global output files
  - Compose: each GRD service depends only on its paired module; facts-total local services depend on the GRD services
  - Apptainer: GRD stage after Stage 2, each service waiting on its own paired outputs; facts-total after it
  - local totals contain GRD outputs for converted modules and the modules' own local outputs for unconverted ones; global totals unchanged
  - ESL unchanged and reading the local total
- Same experiment with `projection_scale: global`: no GRD services, no local totals, no ESL.
- Generated Apptainer script runs end-to-end (e.g. in the Lima VM).
