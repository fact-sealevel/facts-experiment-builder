# `generate-apptainer` Implementation Plan

_Last updated 2026-10-06, against `main` at `7a2ee4e` (#136) and
`add_apptainer_command` at `637acb1`._

## Context

FEB has one code-generation command, `generate-compose`, which produces a Docker
Compose YAML for a FACTS sea-level experiment. This plan adds `generate-apptainer`,
which produces an Apptainer bash script (`experiment-apptainer.sh`) for running the
same experiment on HPC/VM environments without Docker.

The generated script follows the structure of the hand-authored scripts in
`facts2-workspace/apptainer_experiments/` (e.g. `example-coupling-apptainer.sh`,
`small_coupling/experiment-apptainer.sh`).

---

## Status

### `main` (`7a2ee4e`)

Merged since the WIP branch was started (all on top of `ead3e7f` / #127):

| PR | What it changed that matters here |
|---|---|
| #129 | `temperature_service_name` → `climate_service_name` on `generate_compose_service()` / `_build_compose_depends_on()` / `_get_dependency_names()`; manifest key `climate_module`. Fixed the `generate-compose` `TypeError` introduced in #127. |
| #130 | `ExperimentDataPaths` + `resolve_experiment_data_paths(metadata)`; `resolve_experiment_paths()` → `resolve_module_paths()`. **`_build_module_specs()`, `build_experiment_execution_plan()` and `build_module_service_spec()` now require a `data_paths` argument.** |
| #132 | `ExperimentName` validates on construction; `core/experiment/paths.py` removed. |
| #134 | `io/paths.py`: `make_output_dir()` replaced by `check_experiment_does_not_exist()`, `check_experiment_location()`, `create_experiment_dir()`. Setup no longer creates parent dirs or `output/`. |
| #136 | Only the template's path key names are read (`shared-input-data`, `module-specific-input-data`, `output-data-location`); alternative spellings removed. |

### `add_apptainer_command` (`637acb1`, WIP, based on `ead3e7f`)

Steps 1–8 below are implemented in one WIP commit (12 files, +1194 lines):
`ApptainerServiceSpec`, `ModuleServiceSpec.generate_apptainer_service()`,
`ExperimentPaths.apptainer_script_path`, `application/generate_apptainer.py`,
`io/write_apptainer.py`, `templates/apptainer_experiment.sh.j2`,
`cli/generate_apptainer_cli.py`, CLI + `pyproject.toml` registration, and tests
(`test_generate_apptainer.py`, `test_write_apptainer.py`,
`test_generate_apptainer_cli.py`).

**Rebase onto `main`:** `git merge-tree --write-tree main add_apptainer_command`
reports **no textual conflicts**. It will still break at runtime and in tests,
because `generate_apptainer.py` calls `_build_module_specs()` (L221) and
`build_experiment_execution_plan()` (L228) without `data_paths` (required since #130).

Known problems found by running a generated script in a Lima VM:
- Running it with `sh` fails on `set -o pipefail`: the script is bash-only. It must
  be run as `bash experiment-apptainer.sh` or `./experiment-apptainer.sh` (the
  writer already sets the executable bit).
- `fair-temperature` fails with `Got unexpected extra argument (main)`: the leading
  `main` subcommand is not stripped for Apptainer (Compose strips it in
  `build_compose_service_dict()`).
- Harmless warning `Error changing the container working directory ... chdir
  /home/<user>.linux`: `--containall --no-home` hides the home dir; fix with
  `--pwd /`.

Docs: `docs/generate_apptainer.md` and `docs/emma_notes_running_generate_apptainer.md`
exist locally but are untracked, because `docs/` is in `.gitignore` (L188); existing
docs were force-added. Use `git add -f` to commit them.

---

## Architecture

Same four-layer structure as `generate-compose`:

```
CLI → application/generate_apptainer.py → core (ModuleServiceSpec + ApptainerServiceSpec) → io/write_apptainer.py + Jinja2 template
```

Shared pipeline (current `main` signatures):

```
metadata = repo.get(config_path)
plan = _make_experiment_plan(metadata, schemas)
data_paths = resolve_experiment_data_paths(metadata)          # #130
  → (Apptainer only) override output root, see "Remaining work" step 3
specs = _build_module_specs(plan, metadata, schemas, known_module_names, data_paths)
execution_plan = build_experiment_execution_plan(specs, plan, metadata, schemas, data_paths)
  → _build_apptainer_stages(execution_plan) → render + write
```

`_ExecutionPlan` fields used:
- `standard_specs`: climate + sealevel specs → Stage 1 / Stage 2 by `uses_climate_file`
- `facts_total_specs`: `(spec, workflow)` per workflow × output_type → Stage 3
- `esl_specs`: `(spec, depends_on_service_name)` per ESL × workflow → Stage 4
- `standalone_esl_specs`: ESL when no workflows → **not yet run by the script** (see step 6)
- `climate_service_name`, `suppress_output_types`

### `pass_to_total` parity with Compose

**Rule:** the module YAML decides. An output is skipped from totaling services only
if its module YAML sets `pass_to_total: false`; otherwise it is included
(`OutputFileSpec.pass_to_total` defaults to `True`). FEB applies no science-based
filtering of its own. Notes on the current implementation:
- `pass_to_total` exists only on file outputs (`get_file_outputs()`); non-file
  outputs with a matching `output_type` are always included.
- Outputs of a workflow module with no schema in `module_schemas` are included
  unconditionally (backward compatibility); 0.6.0+ configs always have schemas.

This filter lives in **shared** code:
`_collect_workflow_output_paths_by_type()` (`application/execution_plan.py`), which
builds each facts-total spec's `inputs.item` list inside
`_build_facts_total_specs_for_workflows()`. Apptainer Stage 3 is built from
`execution_plan.facts_total_specs` and the template emits each spec's `args`, so the
Apptainer facts-total commands get the same filtered `--item` list as Compose **as
long as Stage 3 keeps using `execution_plan.facts_total_specs`**. Nothing
Apptainer-specific may rebuild the totaling inputs.

Not yet covered by any Apptainer test. Verified for Compose on `main` with
`v2_experiments/BC_my_facts_experiment`: `ipccar5-icesheets` has four
`pass_to_total: False` outputs (`global-wais-output-file`, `global-eais-output-file`,
`local-wais-output-file`, `local-eais-output-file`), and
`facts-total-all-modules-{global,local}` include only its `*-gis-output.nc` and
`*-ais-output.nc`. See Testing and Verification for the Apptainer checks.

---

## Implemented on the WIP branch (Steps 1–8)

Kept for reference; corrections needed after the rebase are listed under
"Remaining work".

### Step 1 — `ApptainerServiceSpec`
`core/module/apptainer_service_spec.py`: frozen dataclass with `service_name`,
`image_name`, `image_tag`, `binds` (`host:container` strings), `args`,
`wait_for_files`, `run_in_background`, `pid_var`. SIF filename is
`{service_name}-{image_tag}.sif` (e.g. `ipccar5-glaciers-0.2.1.sif`).

### Step 2 — `ModuleServiceSpec.generate_apptainer_service()`
Builds `args` from `_build_command_args(suppress_output_types=...)`, `binds` from
`_build_volumes()`, and `image_name` from the last segment of `image_url`.

### Step 3 — `ExperimentPaths.apptainer_script_path`
`io/paths.py`: `_APPTAINER_FILENAME = "experiment-apptainer.sh"` and the property.

### Step 4 — `application/generate_apptainer.py`
`_ApptainerStages` (stage1–4, `all_specs`) and `_build_apptainer_stages()`:
- Stage 1: `standard_specs` with `uses_climate_file == False` (includes climate)
- Stage 2: `standard_specs` with `uses_climate_file == True`, with `wait_for_files`
  for the climate outputs they need
- Stage 3: `facts_total_specs`, `run_in_background=True`,
  `pid_var = f"PID_{service_name.upper().replace('-', '_')}"`
- Stage 4: `esl_specs`, sequential

### Step 5 — Template `templates/apptainer_experiment.sh.j2`
Sections: shebang + `set -euo pipefail`; path vars; global params; `REGISTRY`;
helpers (`log`, `pull_image` with `docker://`, `run_service`, `wait_for_output`);
`mkdir -p`; pull images; Stages 1–4; `log "Experiment complete."`.

### Step 6 — `io/write_apptainer.py`
`render_apptainer_script()` (Jinja2 `PackageLoader`, `StrictUndefined`,
`trim_blocks`, `lstrip_blocks`, `keep_trailing_newline`) and
`write_apptainer_script()` (writes file, sets executable bit).

### Steps 7–8 — CLI and registration
`cli/generate_apptainer_cli.py` (`--experiment-name`, `--workspace-dir`,
`--custom-script-path` with `path_type=Path`, `--debug`); registered in
`cli/__init__.py` and `pyproject.toml`.

---

## Remaining work

In order. Each step should keep the full test suite green.

### Progress (2026-10-06, branch `add_apptainer_command`)

| Step | Status | Notes |
|---|---|---|
| 1. Rebase + `data_paths` | Done (`95595a5`) | Rebased onto `7a2ee4e`. |
| 2. Single source of truth for paths | Done (`95595a5`) | `ModuleServiceSpec.host_output_paths()`; Stage 2 wait files and `OUTPUT_DIR`/`SHARED_IN`/`MODULE_IN` from `data_paths`. Generated script byte-identical to step 1. |
| 3. Apptainer output root | Done (`95595a5`) | `ExperimentPaths.apptainer_output_dir` = `<experiment>/output-apptainer`, applied via `_with_apptainer_output_root()`. Default only (no `--output-dir` flag yet). Generation still creates the output dirs (`ensure_module_output_dir()`); start a new VM session afterwards. |
| 4. Per-service data on `ApptainerServiceSpec` | Done (`95595a5`) | `output_dir`, `registry`, `host_outputs`. Each image is pulled by its own full reference (`image_ref`); the global `REGISTRY` variable was removed, so mixed registries work. |
| 5. Script correctness | Done (uncommitted) | `main` is dropped once in `_build_command_args()` (Compose-only special case removed; Compose output verified byte-identical for BC and `my_facts_experiment`). `envvar` inputs → `env` field → `--env` via `ENV_ARGS` (reset after each service; checked under `set -u` in bash 3.2). `--pwd /` added. |
| 6. Standalone ESL | Done (`95595a5`) | Added to Stage 4 after per-workflow ESL. |
| 7. `pass_to_total` coverage | Verified | BC facts-total `--item` sets match Compose exactly; `ipccar5-icesheets` WAIS/EAIS excluded. Covered by shared `execution_plan` tests; an Apptainer-specific test through `build_experiment_execution_plan()` is still to add. |
| 8. Bind paths via variables | Not started (optional) | |
| 9. Docs | Done (uncommitted) | `docs/generate_apptainer.md` updated (output-apptainer, bash-only, VM flow, full image refs, `pass_to_total`, `envvar`). Needs `git add -f` (docs/ is gitignored). |

Also found: Stage 3 in the template uses `stage3[0].binds` for every facts-total service. Correct today (all facts-total services have the same volumes), but it would silently use the wrong binds if they ever differed.

### 1. Rebase onto `main` and restore the pipeline
- `git rebase main` on `add_apptainer_command` (no textual conflicts expected).
- In `generate_apptainer()`: build `data_paths = resolve_experiment_data_paths(metadata)`
  after `_make_experiment_plan()` and pass it to `_build_module_specs()` and
  `build_experiment_execution_plan()`.
- Update the Apptainer tests' fakes/calls for the new `data_paths` parameter (same
  pattern as #130's test updates).

### 2. Single source of truth for paths in the Apptainer path
Remove every direct read of path keys from `metadata`:
- `generate_apptainer.py` L99 `metadata.get("output-data-location", "")`
  (used for Stage 2 wait files).
- `write_apptainer.py` L21–23 (`output-data-location`, `shared-input-data`,
  `module-specific-input-data`). Take values from `data_paths`, or drop the
  `OUTPUT_DIR` / `SHARED_IN` / `MODULE_IN` template variables, which nothing in the
  template reads.
- Add `ModuleServiceSpec.host_output_paths()` (host paths of outputs on the shared
  output volume, built from `output_paths.output_dir`) and build Stage 2
  `wait_for_files` from the climate spec's `host_output_paths()` and
  `module_definition.get_climate_output_type()`. This replaces re-parsing
  `_build_command_args()` and swapping `/mnt/out` for the raw metadata value.

### 3. Separate Apptainer output root
Goal: run Compose and Apptainer for the same experiment with separate outputs.
- After `resolve_experiment_data_paths()`, apply
  `dataclasses.replace(data_paths, output_data_location=<apptainer root>)` before
  building specs, so binds, mkdir dirs and wait files all follow.
- **Decision open:** where the root comes from: a new config key, or an
  `ExperimentPaths.apptainer_output_dir` default (e.g. `experiment_dir / "output-apptainer"`)
  plus a `--output-dir` CLI flag.
- `ensure_module_output_dir()` creates output dirs at spec-build time on the
  generating machine. If the Apptainer root is a VM-only path (generating on macOS,
  running in Lima), this fails or creates stray dirs. **Decision open:** skip it for
  Apptainer and rely on the script's `mkdir -p`.

### 4. Move per-service data onto `ApptainerServiceSpec`
Add `output_dir`, `registry` and `host_outputs`, filled in by
`generate_apptainer_service()`, so `generate_apptainer.py` reads `ModuleServiceSpec`
only to choose stages. `_compute_mkdir_dirs()` then iterates `stages.all_specs`, and
the registry comes from the specs instead of `spec.components.image.image_url`.

### 5. Correctness fixes in the generated script
- Strip the leading `main` subcommand once, in `_build_command_args()`, for both
  Compose and Apptainer, and remove the special case in
  `build_compose_service_dict()`. Check the Compose output for an affected experiment
  is unchanged.
- `envvar` inputs are skipped by `_build_command_args()` and passed to Compose as
  `environment:`; Apptainer drops them. Pass them with `--env` (needs an `env` field
  on `ApptainerServiceSpec`).
- Add `--pwd /` to `apptainer run` in `run_service`.

### 6. `standalone_esl_specs`
ESL specs when no workflows exist are mkdir'd but never run. Add them as Stage 4
entries with no dependency, or explicitly reject such experiments with a clear error.

### 7. `pass_to_total` regression coverage
No code change expected (see Architecture). Add tests and the BC verification below
so a future change cannot silently pass excluded outputs to Apptainer totaling.

### 8. Optional: bind paths via top-level variables
Express binds as `${OUTPUT_DIR}/...` etc. using a structured bind representation
(root variable + relative suffix + container path), not string-prefix substitution.
Must also cover mkdir dirs and wait files, or editing `OUTPUT_DIR` in the script
would desync them.

### 9. Docs
Force-add `docs/generate_apptainer.md` (`git add -f`), and document running with
`bash`/`./` (not `sh`).

---

## Testing

Existing on the branch: stage grouping, `wait_for_files`, background/PID flags,
template rendering, executable bit, CLI errors. To add:

- **`pass_to_total` (step 7):** with a workflow module whose schema has an output with
  `pass_to_total=False`, the Stage 3 spec's `args` contain no `--item` for it, and do
  contain `--item`s for the module's outputs of the same `output_type` that set
  `pass_to_total=True` **or omit the flag** (default included). Build the stages through `build_experiment_execution_plan()` (not a
  hand-made `_ExecutionPlan`), so the test exercises the shared filter.
- **Parity with Compose:** for the same experiment, each Stage 3 spec's `--item` set
  equals the corresponding Compose facts-total service's `--item` set.
- **Paths (steps 2–3):** wait files and mkdir dirs derive from `output_paths` /
  `data_paths`; with an Apptainer output root override, binds, mkdir dirs and wait
  files all use it, and nothing reads `metadata["output-data-location"]`.
- **`main` stripping (step 5):** a module whose `command` is `main` produces args
  without it, for both Compose and Apptainer.
- **`envvar` inputs (step 5):** rendered script passes them via `--env`.
- **Standalone ESL (step 6).**

---

## Verification

1. `uv run feb generate-apptainer --help` is registered.
2. Generate for `v2_experiments/BC_my_facts_experiment` (from the workspace root):
   - `facts-total-all-modules-global` / `-local` `--item`s include
     `ipccar5-icesheets/{global,local}-{gis,ais}-output.nc` and **exclude**
     `ipccar5-icesheets/*-{wais,eais}-output.nc`.
   - Each facts-total `--item` set equals the one in `experiment-compose.yaml`
     generated from the same config.
3. Generate for `apptainer_experiments/small_coupling` and diff against its
   hand-authored `experiment-apptainer.sh` for structure parity.
4. Run a generated script in the Lima VM with `bash` and confirm `fair-temperature`
   and Stage 2 start (after steps 3 and 5).
5. Full test suite, ruff and pyright on changed files.

---

## Key design decisions

- **SIF name = `{service_name}-{image_tag}`**: a tag mismatch is a visible
  file-not-found error; `ipccar5-glaciers` / `ipccar5-icesheets` stay separate SIFs.
- **`docker://` inside `pull_image`**, not at call sites.
- **`WORKSPACE` baked in** from `--workspace-dir`.
- **Jinja2 for the script.**
- **Bash staging replaces `depends_on`**: sequential blocks, `wait_for_output`
  polling, background `&` + PIDs for Stage 3.
- **Totaling inputs come only from `_ExecutionPlan`**, so the `pass_to_total` filter
  and other totaling rules are shared with Compose.

---

## SIF file management

**Inconsistency to resolve:** the WIP writer uses
`sif_dir = workspace_dir / "apptainer_experiments" / "sif"` (`write_apptainer.py`
L24), but the decision below says `${WORKSPACE}/sif_files/`. Pick one and update the
writer or this section.

Resolved decisions:
- **Versioned SIF filenames** (`{service_name}-{image_tag}.sif`), so multiple versions
  coexist and stale files are never silently reused.
- **Shared SIF directory per workspace**, shared across experiments.
- **No automatic deletion**; a `feb prune-sif` command can come later.
- **`pull_image` skips existing files**; safe because filenames are versioned.

Out of scope: a `feb pull-images` command (analogous to `docker compose pull`).
