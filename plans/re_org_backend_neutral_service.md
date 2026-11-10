# Re-org: ports and adapters for `generate-compose` and `generate-apptainer`

**Branch:** `re_org`. Phases 0–4 were committed as `9c38da4`, based on `add_apptainer_command` at `780aeee`. From Phase 5 on, this plan is based on `add_apptainer_command` at `61d239b` (#152 merged, 2026-11-10). Line numbers are from `61d239b` unless a line says otherwise. All paths are relative to `src/facts_experiment_builder/` unless they start with `tests/` or `plans/`.

**Source:** the "Ports and adapters" tab of the *generate-compose vs generate-apptainer: reuse and parallelism* doc. The first version of this plan (2026-11-04) covered only port 1, the backend-neutral `ServiceRun`. This version also plans ports 2 and 3 (`ExecutionGraph` and `ExecutionBackend`), which were follow-ups before. The original Phases 0–4 are kept, unchanged, in the appendix.

**Rule for every phase:** neither command's output file changes. The Phase 0 snapshot tests prove it. CLI console messages may change where a phase says so.

## Status (2026-11-10)

| Phase | What | State |
| --- | --- | --- |
| 0–4 | `ServiceRun`, `ServiceDependency`; Compose and Apptainer formatting moved from `core/` to `io/` | Done on `re_org` (`9c38da4`), based on `780aeee` |
| 5 | Rebase `re_org` onto `61d239b` | Done: `re_org` is `8961fe5`. The pre-rebase commit is kept as branch `backup/re_org-9c38da4`. |
| 6 | `ExecutionGraph`: one backend-neutral description of what runs and in what order | Done, not committed |
| 7 | `ExecutionBackend` port, Compose and Apptainer adapters, one `generate_run_file()` service | Done, not committed |
| 8 | Shared CLI logging and error handling | Done, not committed |

Phases 6–8 were checked on 2026-11-10. 565 unit tests pass, `ruff check` and `ruff format --check` are clean, and no snapshot changed. The `core/` grep and the Phase 7 `application/` grep print nothing. `generate-compose` and `generate-apptainer`, run through the CLIs on `big_local`, `fair2_global` and `single_esl`, give byte-identical files to the baseline.

Where the Phase 5–8 implementation differs from the plan below:

- **Phase 5 step 2 wasn't needed.** The fixture schemas declare every required field, so the whole-file tests passed without `_fill_in_required_params()`.
- **Phase 6: the "Created ... workflow service" log lines stayed in the Compose adapter** (`io/compose_backend.py`), not in `build_execution_graph()`. Neither command's console output changes. Open question 4 is still open.
- **Phase 7: `render_compose_services(graph)` is a module-level function in `io/compose_backend.py`.** `ComposeBackend.render()` calls it, and the property tests call it directly. `_build_apptainer_stages()`, `_with_apptainer_output_root()` and `_compute_mkdir_dirs()` are module-level functions in `io/apptainer_backend.py`.
- **Phase 7 tests:**
  - `_make_spec()`, `_make_spec_with_outputs()` and `_make_execution_plan()` moved to `tests/unit/helpers.py` as `make_service_spec()`, `make_service_spec_with_outputs()` and `make_execution_plan()`.
  - `tests/unit/test_generate_apptainer.py` became `tests/unit/test_apptainer_backend.py`. Its stage tests go through `build_execution_graph()`.
  - `tests/unit/test_generate_apptainer_cli.py` only imports `main`, so it didn't change.
- **Phase 7 fixed a bug in passing.** `--custom-compose-path` is a `click.Path()` without `path_type`, so it arrives as `str`. The old `generate_compose()` called `.resolve()` on it, which raised `AttributeError`. The Compose CLI now wraps it in `Path`.
- **Phase 8 file names:**
  - `cli/log_handler.py` holds `ClickEchoHandler` and `configure_feb_logging()`, now public names.
  - `application/log_levels.py` holds `SUCCESS` and calls `logging.addLevelName()`.

  These names avoid a module called `logging.py`, which would shadow the standard library if a file in that folder were run directly. `tests/unit/test_generate_compose_cli.py` became `tests/unit/test_cli_log_handler.py`.
- **Phase 8 step 4 (optional) was done.** The Compose CLI's "Next steps" line uses `_display_path()`, so it no longer crashes when the workspace is outside the current directory.

Where the Phase 0–4 implementation differs from the appendix:

- **Phase 0 stores expected values as snapshot files** (`tests/unit/snapshots/`), not literals in the test. Regenerate with `FEB_UPDATE_SNAPSHOTS=1` only for an intended output change. The whole-file tests use six module YAMLs copied from `facts-module-registry` at `a085795` into `tests/unit/fixtures/module_registry/`.
- **Phase 3: facts-total and ESL still set `depends_on` after building the service dict**, instead of passing `ServiceDependency` lists to `to_compose_service()`. `build_compose_service_dict()` drops an empty `depends_on`, so a workflow with no modules (which `Workflow` allows) would have lost its `depends_on: {}` key. Phase 7 moves this into the Compose adapter.
- **Adapters are in `io/`** (D3): `io/apptainer_service.py`, `io/compose_service.py`.

## What changed on `add_apptainer_command` since `780aeee`

| Commit | Change | Effect on this plan |
| --- | --- | --- |
| `d0cd6eb` | New `application/prepare_plan.py`: `prepare_execution_plan(config, data_paths) -> (_ExperimentPlan, _ExecutionPlan)`, shared by both commands. `_build_compose_services()` became `render_compose_services(execution_plan)`. `_ModuleSpecs.is_empty` added. | Done: the shared-setup follow-up in the first plan ("`prepare_experiment()`"). Conflicts with `9c38da4` in both `generate_*.py` files (Phase 5). |
| `61d239b` (#152) | `ExperimentRepository.get()` returns `LoadedExperimentConfig` (`core/experiment/loaded_config.py`), which checks required fields and int types. `check_metadata_has_required_fields()` and both `_REQUIRED_FIELDS` lists in `experiment_plan.py` and `generate_compose.py` removed. | The Apptainer adapter can read typed values (`config.nsamps`, ...) instead of `metadata.get(...)` (Phase 7). Configs in tests must have every required field (Phase 5). |

## Where duplication and backend logic are now

`core/` is clean on `re_org` (Phases 1–4). What's left is in `application/`, `io/` and `cli/`:

| Code | Location (`61d239b`) | Problem |
| --- | --- | --- |
| Experiment path setup, output-path override, config-exists `assert`, `repo.get()`, `resolve_experiment_data_paths()` | `generate_compose()` (`application/generate_compose.py:69-126`) and `generate_apptainer()` (`application/generate_apptainer.py:155-216`) | Same steps written twice. Compose also asserts `experiment_dir.is_dir()`; Apptainer doesn't. The `assert`s are disabled under `python -O`, and the Compose CLI doesn't catch `AssertionError`. |
| Dependency order | Compose: `ModuleServiceSpec.dependencies()` (on `re_org`) plus the facts-total and ESL `depends_on` in `render_compose_services()` (`generate_compose.py:39-66`). Apptainer: stage split in `_build_apptainer_stages()` (`generate_apptainer.py:72-131`) and `_get_climate_wait_files()` (`:55-69`). | The same ordering is worked out twice, in two forms. |
| `suppress_output_types` | Passed for standard specs only, in both `render_compose_services()` and `_build_apptainer_stages()` | The same rule written twice. |
| Apptainer-only steps | `_with_apptainer_output_root()` (`:134-147`), `_compute_mkdir_dirs()` (`:150-152`), `_ApptainerStages` (`:33-43`), PID variable names | Backend logic in `application/`. |
| Writing the file | Compose: the CLI writes it (`cli/generate_compose_cli.py`, `make_compose_yaml()` + `write_compose_yaml()`). Apptainer: `generate_apptainer()` writes it (`write_apptainer_script()`). | The two commands split work between layers differently. |
| `application/` imports adapters | `generate_apptainer.py:22-25` imports `io.write_apptainer`. On `re_org`, also `io.apptainer_service` and `io.compose_service`. | `application/` depends on the adapters, not the other way round. |
| `io/write_apptainer.py:8` imports `application.execution_plan._ExecutionPlan` | `_build_template_context()` reads `metadata.get("nsamps", "")` and similar | It reads the raw dict that `LoadedExperimentConfig` now types. |
| `_SUCCESS = 25` and `_log_success()` | `prepare_plan.py`, `generate_compose.py`, `generate_apptainer.py`, both CLIs (five copies of `_SUCCESS`) | Duplicated. |
| `_ClickEchoHandler`, `_configure_feb_logging()` | `cli/generate_compose_cli.py`, `cli/generate_apptainer_cli.py` | Duplicated. |

## Goal

When Phases 5–8 are done:

- One application service, `generate_run_file()`, runs every step both commands share. It takes an `ExecutionBackend` and imports no Compose or Apptainer code.
- One backend-neutral `ExecutionGraph` says what runs, with which `ServiceRun`, after what, and waiting for which files. Both backends read it.
- The Compose and Apptainer adapters in `io/` implement `ExecutionBackend`. Each holds only formatting and writing.
- The CLI is the only place that picks an adapter (the composition root), as it already does for `StorageExperimentRepository`.
- Both commands write byte-identical files to `780aeee`, checked by the Phase 0 snapshots.
- Adding a backend (AsyncFlow, for example) means writing one adapter and one CLI command.

Target layout:

```text
cli/generate_compose_cli.py      ─┐ pick ComposeBackend / ApptainerBackend,
cli/generate_apptainer_cli.py    ─┘ call generate_run_file()
cli/logging.py                      shared _ClickEchoHandler, configure_feb_logging()   (Phase 8)

application/generate_run_file.py    generate_run_file(): the one service              (Phase 7)
application/backend.py              ExecutionBackend Protocol, RunInfo (port)         (Phase 7)
application/execution_graph.py      ExecutionGraph, ServiceNode, Stage, build_*()     (Phase 6)
application/prepare_plan.py         prepare_execution_plan() (unchanged)
application/execution_plan.py       _ExecutionPlan (unchanged)
application/storage.py              ExperimentRepository (unchanged port)

io/compose_backend.py               ComposeBackend (adapter)                          (Phase 7)
io/compose_service.py               to_compose_service() (re_org)
io/apptainer_backend.py             ApptainerBackend (adapter)                        (Phase 7)
io/apptainer_service.py             ApptainerServiceSpec, to_apptainer_service() (re_org)
io/write_apptainer.py               template rendering (reads RunInfo, not metadata)
io/write_compose.py                 make_compose_yaml(), write_compose_yaml() (unchanged)

core/module/service_run.py          ServiceRun, ServiceDependency (re_org)
```

Removed: `application/generate_compose.py`, `application/generate_apptainer.py`.

## Decisions

D1–D4 (in the appendix) still apply. New:

**D5. The `ExecutionGraph` lives in `application/`, next to `_ExecutionPlan`.** It is built from `_ExecutionPlan`, which is in `application/`. It holds only `core/` types (`ServiceRun`, `ServiceDependency`), so it could move to `core/` later.

**D6. A graph node records its stage; the Apptainer adapter doesn't work stages out again.** Today `_build_apptainer_stages()` assigns stages from three facts: which `_ExecutionPlan` field a spec is in, whether it is the climate service, and `uses_climate_file`. The graph builder sets `node.stage` from the same facts. Working stages out from the dependencies instead (a topological `levels()`) would put facts-total in an earlier stage when every workflow module is in Stage 1, which changes the Apptainer script. That belongs in the parallel-levels follow-up, which is allowed to change output.

**D7. Settings that differ between backends are adapter arguments.** `run_in_background`, `pid_var`, the SIF directory, the default `"service_completed_successfully"` condition, and keeping `depends_on: {}` for facts-total and ESL are decided in the adapters. The graph holds only what both backends use.

**D8. Adapters write their own file.** `ExecutionBackend.write()` does the I/O, and `generate_run_file()` calls it. Writing then happens in the same layer for both commands. Today the Compose CLI writes the file, and `generate_apptainer()` writes the Apptainer one.

**D9. Missing experiment directory or config raises `FileNotFoundError`, not `assert`.** The file output doesn't change. The console message for this error changes slightly, and the Compose CLI starts catching it cleanly.

## Phase 5: rebase `re_org` onto `61d239b`

`re_org` is one commit (`9c38da4`) on `780aeee`. A dry-run merge (`git merge-tree 61d239b 9c38da4`) conflicts in two files only:

| File | Resolve by |
| --- | --- |
| `application/generate_compose.py` | Keep `61d239b`'s structure (`render_compose_services()`, `prepare_execution_plan()`, no `_REQUIRED_FIELDS`). Apply `9c38da4`'s change inside `render_compose_services()`: standard specs call `to_compose_service(spec.to_service_run(suppress_output_types=...), depends_on=spec.dependencies(climate_service_name=...))`, and facts-total and ESL call `to_compose_service(spec.to_service_run())` and then set `depends_on` as now. Add the `io.compose_service` import. Drop `9c38da4`'s return-type comment (`# dict[str, Any]:`). |
| `application/generate_apptainer.py` | Keep `61d239b`'s `generate_apptainer()` (uses `prepare_execution_plan()` and `config.raw`). Apply `9c38da4`'s `to_apptainer_service(spec.to_service_run(...), ...)` calls in `_build_apptainer_stages()`, and its import change (`io.apptainer_service` instead of `core.module.apptainer_service_spec`). Don't bring back `9c38da4`'s imports of `_make_experiment_plan` or `ModuleSchema`; `61d239b` no longer needs them. |

Steps:

1. `git rebase --onto add_apptainer_command 780aeee re_org`, and resolve as above.
2. `tests/unit/test_service_output_characterization.py` (`_setup_experiment()`, `9c38da4`) runs `setup-experiment` and then both generators. `LoadedExperimentConfig` now rejects configs missing a required field. `setup-experiment` writes only the top-level parameters that the modules' schemas declare (`collect_metadata_param_keys()`). If the six fixture schemas don't declare all of them, the whole-file tests fail with "experiment-config.yaml is missing values for: ...". In that case, move `_REQUIRED_PARAMS` and `_fill_in_required_params()` from `tests/unit/test_scenario_passthrough.py` to `tests/unit/helpers.py`, and call it in `_setup_experiment()`. Not checked yet.
3. Check the files `9c38da4` changed that the merge resolved automatically: `application/execution_plan.py` (docstring only), `core/experiment/experiment_plan.py` (docstring only) and `tests/unit/test_generate_compose_property.py` (`_stub_spec()` now stubs `to_service_run` and `dependencies`; check it matches `61d239b`'s use of `render_compose_services(exec_plan)`).

**Done when:** all tests pass with no snapshot changes; `grep -rniE "compose|apptainer|docker" src/facts_experiment_builder/core` prints nothing. `d0cd6eb` and `61d239b` were checked to give byte-identical output to `780aeee`, so the snapshots should still match. A snapshot change here means the conflict was resolved wrongly.

## Phase 6: `ExecutionGraph`

Create `application/execution_graph.py`:

```python
class Stage(Enum):
    """Experiment step a service belongs to. Services in a later stage use outputs
    from earlier ones."""

    INDEPENDENT = 1        # climate module, and sea-level modules without uses_climate_file
    NEEDS_CLIMATE = 2      # sea-level modules with uses_climate_file
    TOTALING = 3           # facts-total, one per workflow × output type
    EXTREME_SEALEVEL = 4   # ESL, one per module × workflow


@dataclass(frozen=True)
class ServiceNode:
    run: ServiceRun
    stage: Stage
    depends_on: list[ServiceDependency]  # services that must finish first
    wait_for_files: list[str]            # host paths to wait for (climate outputs)


@dataclass(frozen=True)
class ExecutionGraph:
    """What runs, after what, and waiting for which files. Read by every backend."""

    nodes: dict[str, ServiceNode]  # in run order: climate, sea-level, facts-total, ESL
    climate_service_name: str | None

    def in_stage(self, stage: Stage) -> list[ServiceNode]: ...


def build_execution_graph(execution_plan: _ExecutionPlan) -> ExecutionGraph: ...
```

`build_execution_graph()` contains what is now spread over `render_compose_services()` and `_build_apptainer_stages()`:

1. **Standard specs, in `standard_specs` order.** `run = spec.to_service_run(suppress_output_types=execution_plan.suppress_output_types)`. `depends_on = spec.dependencies(climate_service_name=execution_plan.climate_service_name)`. Stage is `INDEPENDENT` for the climate service or when `not spec.module_definition.uses_climate_file`, and `NEEDS_CLIMATE` otherwise. `wait_for_files` is set only for `NEEDS_CLIMATE`, from the climate node's `run.host_outputs`, moving `_get_climate_wait_files()` here. With no climate service it is `[]`, as now.
2. **facts-total, in `facts_total_specs` order.** `run = spec.to_service_run()` (no `suppress_output_types`, as now). `depends_on = [ServiceDependency(m) for m in wf.module_names]`. Stage `TOTALING`. `wait_for_files = []`.
3. **ESL, in `esl_specs` order.** `run = spec.to_service_run()`. `depends_on = [ServiceDependency(depends_on_service)]`. Stage `EXTREME_SEALEVEL`.

Node order matches both current outputs. Compose's service order is standard, facts-total, ESL. Apptainer's stage lists are those nodes filtered by stage, keeping order. The climate service is first in `standard_specs` (`build_experiment_execution_plan()`), which puts it first in Stage 1, as `_build_apptainer_stages()` does.

Move the `_log_success("Created %s workflow service", ...)` and `"Created %s ESL workflow service"` calls from `render_compose_services()` into `build_execution_graph()`. The Apptainer command doesn't log these messages today, so its console output gains two lines per workflow. Note this in the CHANGELOG, or drop the messages from both commands.

Tests, in `tests/unit/test_execution_graph.py`:

- stage of each kind of spec, including `uses_climate_file` with and without a climate service
- `wait_for_files` keeps only the climate outputs named by the module's `climate_step_output` inputs (moved from the `_get_climate_wait_files()` tests in `tests/unit/test_generate_apptainer.py`)
- `suppress_output_types` reaches standard nodes only
- node order for an experiment with climate, two sea-level modules, two workflows and ESL

This phase only adds code; no caller uses the graph yet.

**Done when:** new tests pass; existing tests and snapshots unchanged.

## Phase 7: `ExecutionBackend` port, adapters, and `generate_run_file()`

### 7a. The port: `application/backend.py`

```python
@dataclass(frozen=True)
class RunInfo:
    """Experiment-level values a backend may need besides the services."""

    config: LoadedExperimentConfig
    data_paths: ExperimentDataPaths   # after ExecutionBackend.data_paths()
    workspace_dir: Path
    workflow_names: list[str]         # _ExperimentPlan.workflows keys, in order


class ExecutionBackend(Protocol):
    """Port for turning an ExecutionGraph into a run file (Compose YAML, bash script)."""

    def default_output_path(self, experiment_paths: ExperimentPaths) -> Path: ...
    def data_paths(
        self, data_paths: ExperimentDataPaths, experiment_paths: ExperimentPaths
    ) -> ExperimentDataPaths: ...
    def render(self, graph: ExecutionGraph, info: RunInfo) -> str: ...
    def write(self, content: str, path: Path) -> None: ...
```

`data_paths()` is how Apptainer moves its output root (`_with_apptainer_output_root()`). It runs before `prepare_execution_plan()`, because module specs fix their paths when they are built. Compose returns `data_paths` unchanged.

`ExperimentPaths` is in `io/paths.py`, and `application/` already imports it (`generate_compose.py:21`, `setup_experiment.py:25`). Moving it is out of scope.

### 7b. The service: `application/generate_run_file.py`

```python
@dataclass(frozen=True)
class GenerateRunFileOutput:
    path: Path


def generate_run_file(
    experiment_name: str,
    workspace_dir: Path,
    experiment_repo: ExperimentRepository,
    backend: ExecutionBackend,
    custom_output_path: Path | None = None,
) -> GenerateRunFileOutput:
    experiment_paths = ExperimentPaths(workspace_dir=..., experiment_name=ExperimentName.parse(...))
    output_path = custom_output_path.resolve() if custom_output_path else backend.default_output_path(experiment_paths)
    # FileNotFoundError if experiment dir or config is missing (D9)
    config = experiment_repo.get(config_path=experiment_paths.config_path)
    data_paths = backend.data_paths(resolve_experiment_data_paths(config.raw), experiment_paths)
    plan, execution_plan = prepare_execution_plan(config, data_paths)
    graph = build_execution_graph(execution_plan)
    content = backend.render(graph, RunInfo(config, data_paths, workspace_dir, list(plan.workflows)))
    backend.write(content, output_path)
    return GenerateRunFileOutput(path=output_path)
```

Delete `application/generate_compose.py` and `application/generate_apptainer.py`. Nothing in `application/` imports an adapter after this.

### 7c. Compose adapter: `io/compose_backend.py`

`ComposeBackend`:

- `default_output_path()` returns `experiment_paths.compose_path`.
- `data_paths()` returns its input unchanged.
- `render()` builds `{"services": {name: ...}}` from `graph.nodes` with `to_compose_service(node.run, node.depends_on)`, then returns `make_compose_yaml(...)`. For `TOTALING` and `EXTREME_SEALEVEL` nodes, set `depends_on` after building, as now, so an empty workflow keeps `depends_on: {}` (see the Status deviation for Phase 3). Comment on why.
- `write()` calls `write_compose_yaml()`.

Compose stops using `node.stage` and `node.wait_for_files`.

### 7d. Apptainer adapter: `io/apptainer_backend.py`

`ApptainerBackend` moves these out of `application/generate_apptainer.py`:

- `_ApptainerStages`, built from `graph.in_stage(...)` with `to_apptainer_service()`. Stage 2 passes `wait_for_files=node.wait_for_files`. Stage 3 passes `run_in_background=True, pid_var=f"PID_{name.upper().replace('-', '_')}"`.
- `_compute_mkdir_dirs()`.
- `data_paths()` from `_with_apptainer_output_root()`.
- `default_output_path()` returns `experiment_paths.apptainer_script_path`.
- `render()` calls `render_apptainer_script()`.
- `write()` calls `write_apptainer_script()`.

Change `io/write_apptainer.py`:

- `_build_template_context()` takes `RunInfo` instead of `metadata`, `data_paths`, `workspace_dir` and `workflow_vars`. It reads `str(info.config.nsamps)` and the like instead of `str(metadata.get("nsamps", ""))`. `LoadedExperimentConfig` guarantees these fields are set, so the `""` fallbacks go. Required ints are rendered by `str()`, as now, so the script doesn't change.
- `workflow_vars` is built from `info.workflow_names`, moved from `generate_apptainer()` (`generate_apptainer.py:200-203`).
- `climate_service_name` comes from `graph.climate_service_name`.
- Drop the import of `application.execution_plan._ExecutionPlan`. Import `ExecutionGraph` and `RunInfo` instead. An adapter importing a port's types is the intended direction.

### 7e. CLIs

- `cli/generate_compose_cli.py`: call `generate_run_file(..., backend=ComposeBackend(), custom_output_path=custom_compose_path)`. Remove the CLI's own `make_compose_yaml()` / `write_compose_yaml()` calls; its "Step 3/4/5" console lines go or are reworded.
- `cli/generate_apptainer_cli.py`: call `generate_run_file(..., backend=ApptainerBackend(), custom_output_path=custom_script_path)`.
- Both keep their own flags, titles and "Next steps" text.

### 7f. Tests

| Test file | Change |
| --- | --- |
| `tests/unit/test_service_output_characterization.py` | Whole-file tests call `generate_run_file()` with each backend and read the written file. Per-service tests don't change. **Snapshots must not change.** |
| `tests/unit/test_generate_apptainer.py` | Becomes `tests/unit/test_apptainer_backend.py`: stage tests build an `ExecutionGraph` instead of an `_ExecutionPlan`. `_get_climate_wait_files()` tests moved in Phase 6. `_with_apptainer_output_root()` tests call `ApptainerBackend().data_paths()`. |
| `tests/unit/test_generate_compose_property.py` | Tests of `render_compose_services(exec_plan)` call `ComposeBackend().render(build_execution_graph(exec_plan), info)`, or assert on the graph. `_stub_spec()` stays. |
| `tests/unit/test_write_apptainer.py` | Pass `RunInfo` instead of `metadata`; build it with `LoadedExperimentConfig.from_dict(make_config_raw(...))`. |
| `tests/unit/test_scenario_passthrough.py` | Call `generate_run_file()` with each backend. |
| New `tests/unit/test_generate_run_file.py` | A fake backend that records its calls: `data_paths()` runs before planning, `render()` gets the graph, `write()` gets the resolved path, `custom_output_path` wins over `default_output_path()`, missing config raises `FileNotFoundError`. |

**Done when:**

- All tests pass.
- Snapshots unchanged.
- `grep -rnE "io\.(compose|apptainer|write_compose|write_apptainer)" src/facts_experiment_builder/application` prints nothing.
- Manual: both commands give byte-identical files to `780aeee` on the scratch experiments (see Verification).

## Phase 8: shared CLI logging and error handling

1. Create `cli/logging.py` with `_ClickEchoHandler` and `configure_feb_logging()` (the Compose CLI's version, which has the docstring). Both generate CLIs import it. They are the only two copies (`grep -rl "class _ClickEchoHandler" src`).
2. One `SUCCESS = 25` constant, for example in `application/logging.py`, imported by `application/` modules and `cli/logging.py`. This replaces the five copies of `_SUCCESS = 25` and the "must match" comments.
3. Both CLIs catch the same errors: `FileNotFoundError` and `ValueError`. After D9, `AssertionError` no longer needs catching.
4. Optional, changes console output only: `generate_compose_cli.py` prints `compose_path.relative_to(Path.cwd())`, which raises `ValueError` when the workspace isn't under the current directory. Print the path relative to cwd when it is under cwd, and the absolute path otherwise.

**Done when:** tests pass; the CLI tests still pass; no CLI module defines its own log handler.

## Verification (after each phase)

1. `uv run pytest -q tests/unit`: everything passes, and snapshot files are unchanged (`git status tests/unit/snapshots` is clean).
2. `uv run ruff check` and `uv run ruff format --check`.
3. Manual: set up the scratch experiments `big_local`, `fair2_global` and `single_esl` from `../facts-module-registry` (`setup_exps.py` in the session scratchpad), run both commands from `780aeee` and from the phase's commit, then `diff` the outputs. Use `uv run generate-compose ...` and `uv run generate-apptainer ...`. A globally installed `feb` in `~/.local/bin` may shadow the repo code, so check `which` first.

## Follow-ups (scoped, not planned here)

| Follow-up | Size | Depends on | Changes output? |
| --- | --- | --- | --- |
| No-climate-module bugs in `_build_module_specs()` (`prepare_plan.py:124`, `:138-140`): `schemas[plan.climate_module_name]` raises `KeyError: 'NONE'` before the `NONE` check, and `_validate_climate_file_inputs()` is passed the empty `sealevel_modules` dict, not `plan.sealevel_module_names` | Small | Nothing | Yes: configs that crash today would generate |
| Opt-in parallel levels in the Apptainer script, from a topological `ExecutionGraph.levels()` (see D6) | Medium | Phase 6; SIF naming fix (review note 4 in `plans/pr137_summary.md`) | Yes |
| Planning creates output directories (`ensure_module_output_dir()`, `module_service_spec_factory.py:62`). Move this to the backend's `write()` step or a file-system port | Small | Phase 7 | No file change; directories created later |
| Make `_make_experiment_plan()` and `_build_module_specs()` take `LoadedExperimentConfig` instead of `config.raw` | Medium | Nothing | No |
| Merge `_ExecutionPlan` into `ExecutionGraph` if nothing else reads `_ExecutionPlan` after Phase 7 | Small | Phase 7 | No |
| AsyncFlow backend: a third adapter, which tests whether the port is enough | Medium | Phase 7 | New output only |

`plans/add_rsl_step.md` and `plans/add_grd_via_module_flags.md` describe ordering for Compose and Apptainer separately. After Phase 6 they only need to set each new node's `stage` and `depends_on` in `build_execution_graph()`.

## Open questions

1. **Merge target for `re_org`:** a PR into `add_apptainer_command` (stacked on #137), or into `main` after #137 merges? Phase 5 assumes `add_apptainer_command` at `61d239b`. If #137 merges first, rebase onto `main` instead; the conflicts are the same.
2. **One PR or several?** Phases 5, 6–7 and 8 can be separate PRs. Phase 6 alone adds unused code, so it's easier to review together with Phase 7.
3. **Keep `generate_compose()` / `generate_apptainer()` as thin wrappers?** The plan deletes them. Keeping them would mean `application/` imports the adapters again, which is the dependency Phase 7 removes.
4. **The "Created ... workflow service" log lines (Phase 6):** add them to the Apptainer command, or remove them from both?
5. **Empty-workflow `depends_on: {}` (Phase 7c):** keep reproducing it, or allow this output change and drop the special case? A `Workflow` with no modules may not be reachable from `setup-experiment`; check before deciding.
6. From the first plan, still open: image URL trailing slash (D4), and a `Mount` type instead of `"host:container"` strings.

---

## Appendix: the 2026-11-04 plan for Phases 0–4 (done on `re_org`, `9c38da4`)

Kept unchanged for reference. Line numbers are from `780aeee`.

### Context: what is backend-specific in `core/` today

| Code | Location | Backend |
| --- | --- | --- |
| `import ApptainerServiceSpec` | `core/module/module_service_spec.py:9-11` | Apptainer |
| `ModuleServiceSpec._get_dependency_names()` | `core/module/module_service_spec.py:467-495` | Neutral, but unused; duplicates the logic below |
| `ModuleServiceSpec._build_compose_depends_on()` | `core/module/module_service_spec.py:497-529` | Compose |
| `ModuleServiceSpec.generate_compose_service()` | `core/module/module_service_spec.py:549-577` | Compose |
| `ModuleServiceSpec.generate_apptainer_service()` | `core/module/module_service_spec.py:595-634` | Apptainer |
| `build_compose_service_dict()` | `core/module/module_service_spec.py:851-end` | Compose |
| `ApptainerServiceSpec` | `core/module/apptainer_service_spec.py` (whole file) | Apptainer |
| Docstrings/comments naming Compose or Apptainer | see Phase 5 | Wording only |

Both `generate_*_service()` methods already compute the same four things, `_build_command_args(suppress_output_types=...)`, `_build_volumes()`, `_build_environment()` and the image, and differ only in how they package them. `generate_apptainer_service()` also adds `output_dir` and `host_output_paths()`.

Callers:

- `application/generate_compose.py:294, 300, 309` (`_build_compose_services()`) call `generate_compose_service()`.
- `application/generate_apptainer.py:97, 109, 114, 123, 133` (`_build_apptainer_stages()`) call `generate_apptainer_service()`; the module imports `ApptainerServiceSpec` (`:23-25`).
- `io/write_apptainer.py` uses `ApptainerServiceSpec` fields through the template; it does not import the class.

### Decisions

**D1. `ServiceRun` lives in `core/module/service_run.py`.** It is a frozen dataclass with no backend vocabulary:

```python
@dataclass(frozen=True)
class ServiceRun:
    """Everything needed to run one module service, independent of how it is run."""

    name: str
    image: ModuleContainerImage    # image_url + image_tag, unchanged
    args: list[str]                # _build_command_args(suppress_output_types=...)
    binds: list[str]               # "host:container", as _build_volumes() returns
    env: dict[str, str]            # _build_environment()
    output_dir: str                # components.output_paths.output_dir
    host_outputs: dict[str, str]   # host_output_paths(), NOT filtered by suppress_output_types
```

`binds` stays as `"host:container"` strings. Both Docker volumes and Apptainer `--bind` use that syntax, so a `Mount` type isn't needed yet (see Open questions).

**D2. Dependencies become a neutral list.** `core/module/service_run.py` also gets:

```python
@dataclass(frozen=True)
class ServiceDependency:
    service: str
    condition: str | None = None   # only set when the module YAML gives one
```

`ModuleServiceSpec.dependencies(climate_service_name) -> list[ServiceDependency]` replaces both `_get_dependency_names()` and `_build_compose_depends_on()`. It keeps their shared rules: the climate service is added when `uses_climate_file` is set, and `"fair"` maps to `climate_service_name`. `condition` is `None` unless a dict entry in the schema's `depends_on` sets one. The Compose adapter supplies the `"service_completed_successfully"` default, so that Compose term leaves `core/`.

To keep output identical, the adapter has to build its dict in list order, so a repeated name keeps its first position and its last value. That is how the current `dict` assignment in `_build_compose_depends_on()` behaves.

**D3. Adapters go in `io/`.** Recommended, and matches the target layout in the doc:

- `io/apptainer_service.py`: `ApptainerServiceSpec` (moved unchanged) and `to_apptainer_service(run, *, wait_for_files=None, run_in_background=False, pid_var=None)`.
- `io/compose_service.py`: `build_compose_service_dict()` (moved unchanged) and `to_compose_service(run, depends_on=())`.

`application/` already imports from `io/` (`io.paths`, `io.write_apptainer`), so this adds no new dependency direction. When the `ExecutionBackend` port lands (Follow-ups), these become internals of `ComposeBackend` and `ApptainerBackend`. **Alternative:** `application/backends/`. See Open questions.

**D4. Each adapter keeps its own image formatting exactly.** Compose uses `f"{image_url}:{image_tag}"` with `image_url` as given. Apptainer does `image_url.rstrip("/")` and then `rpartition("/")` into registry and image name. These differ for a URL with a trailing `/`. Don't unify them in this work; that would change output (see Open questions).

### Phase 0: tests that pin current output (before any code change)

Add `tests/unit/test_service_output_characterization.py`. Every assertion compares a **whole** value, not selected fields, so any change shows up.

1. **Per-service output.** Build the current Compose dict (`spec.generate_compose_service(...)`) and `ApptainerServiceSpec` (`spec.generate_apptainer_service(...)`) for each case below. Write the full expected value as a literal in the test. Reuse `_make_spec()` / `_make_spec_with_outputs()` from `tests/unit/test_generate_apptainer.py` and the `output_spec` fixture pattern from `tests/unit/test_module_service_spec.py`. If several test files need these helpers, move them to `tests/unit/helpers.py`.
   - plain module, no outputs
   - module with outputs on the shared output volume, and `suppress_output_types={"local"}`
   - module with an `envvar` input
   - `uses_climate_file=True` with `climate_service_name` given, and with `None`
   - schema `depends_on` with a string entry, a dict entry with `condition`, a dict entry without one, and the `"fair"` mapping
   - facts-total-style spec with `output_container_base`
   - image URLs: `ghcr.io/org/img`, `img` (no registry), `ghcr.io/org/img/` (trailing slash)
   - Apptainer extras: `wait_for_files`, `run_in_background=True` + `pid_var`
2. **Whole files.** Set up a workspace as `tests/unit/test_scenario_passthrough.py` does (`prepare_experiment_setup()` + `finalize_experiment_setup()` into `tmp_path`). Run `generate_compose()` (then `make_compose_yaml()`) and `generate_apptainer()`, replace `str(tmp_path)` with a placeholder, and compare with snapshot files under `tests/unit/snapshots/`. The `make_schema()` schemas in that test have no volumes or outputs. Give at least one schema an output on the shared volume, a climate input with `climate_step_output`, and an `envvar` input, so the snapshots cover binds, wait files and env. Use one ESL-free experiment and one with ESL (two workflows) so all four Apptainer stages appear.
3. Generate the snapshots once, on `re_org` before Phase 1, and commit them with the tests.

**Done when:** the new tests pass on unmodified code, and `uv run pytest -q tests/unit` shows 523 + new passing.

### Phase 1: add `ServiceRun` and `dependencies()` (in scope)

1. Create `core/module/service_run.py` with `ServiceRun` and `ServiceDependency` (D1, D2).
2. Add to `ModuleServiceSpec`:
   ```python
   def to_service_run(self, suppress_output_types: set | None = None) -> ServiceRun:
       return ServiceRun(
           name=self.module_name,
           image=self.components.image,
           args=self._build_command_args(suppress_output_types=suppress_output_types),
           binds=self._build_volumes(),
           env=self._build_environment(),
           output_dir=self.components.output_paths.output_dir,
           # All outputs: other services may wait on outputs this one writes,
           # whatever is passed downstream (comment moved from generate_apptainer_service).
           host_outputs=self.host_output_paths(),
       )

   def dependencies(self, climate_service_name: str | None = None) -> list[ServiceDependency]: ...
   ```
3. Rewrite `generate_compose_service()` and `generate_apptainer_service()` as thin wrappers over `to_service_run()` and `dependencies()`. They still live in `core/` for now. Delete `_get_dependency_names()`; it has no callers. Rewrite `_build_compose_depends_on()` to build its dict from `dependencies()`.
4. Add unit tests for `to_service_run()` and `dependencies()` in `tests/unit/test_module_service_spec.py`.

**Done when:** Phase 0 tests pass unchanged. Any change to a Phase 0 test in this phase is a bug.

### Phase 2: move Apptainer formatting out of `core/` (in scope)

1. Create `io/apptainer_service.py`. Move `ApptainerServiceSpec` there unchanged; update its docstring's "Built by" line. Add `to_apptainer_service(run, *, wait_for_files=None, run_in_background=False, pid_var=None)`, with the registry/image-name split moved from `generate_apptainer_service()` (`module_service_spec.py:616-618`).
2. In `application/generate_apptainer.py`, replace each `spec.generate_apptainer_service(**kw)` with `to_apptainer_service(spec.to_service_run(suppress_output_types=...), **rest)`. Pass `suppress_output_types` only where it is passed today: Stages 1 and 2, not 3 or 4. Update the import at `:23-25`.
3. Delete `generate_apptainer_service()`, `core/module/apptainer_service_spec.py`, and the import at `module_service_spec.py:9-11`.
4. Update the tests:

| Test file | Change |
| --- | --- |
| `tests/unit/test_generate_apptainer.py` | Import `ApptainerServiceSpec` from `io.apptainer_service`. The `generate_apptainer_service()` unit tests (`:184-230`, `:447-475`) call `to_apptainer_service(spec.to_service_run(), ...)` instead; their assertions don't change. |
| `tests/unit/test_write_apptainer.py` | Import path only (`:8-10`). |
| `tests/unit/test_module_service_spec.py` | `:300-301` and `:341-342` compare Compose and Apptainer output. Compare via the two adapters, or replace with one `to_service_run()` assertion. Their point, that both backends get the same args and env, is now true by construction. |
| `tests/unit/test_service_output_characterization.py` | Apptainer cases switch to the new call; expected literals don't change. |

**Done when:** all tests pass; no file under `core/` mentions Apptainer outside docstrings (Phase 5 handles those).

### Phase 3: move Compose formatting out of `core/` (in scope)

1. Create `io/compose_service.py`. Move `build_compose_service_dict()` there unchanged. Add:
   ```python
   def to_compose_service(run: ServiceRun, depends_on: Iterable[ServiceDependency] = ()) -> dict[str, Any]:
       deps = {d.service: {"condition": d.condition or "service_completed_successfully"} for d in depends_on}
       return build_compose_service_dict(
           image_str=f"{run.image.image_url}:{run.image.image_tag}",
           command=run.args, volumes=run.binds, depends_on=deps, environment=run.env,
       )
   ```
2. In `application/generate_compose.py` `_build_compose_services()`:
   - standard specs (`:293-297`): `to_compose_service(spec.to_service_run(suppress_output_types=...), spec.dependencies(execution_plan.climate_service_name))`
   - facts-total (`:299-306`) and ESL (`:308-314`): `to_compose_service(spec.to_service_run(), [ServiceDependency(m) for m in wf.module_names])` and `[ServiceDependency(depends_on_service)]`. This replaces setting `compose_svc["depends_on"]` afterwards. Check key order in the output: today `depends_on` is set after `build_compose_service_dict()` returns. Since `build_compose_service_dict()` also adds `depends_on` last, the order should match. The Phase 0 snapshot will confirm it.
3. Delete `generate_compose_service()`, `_build_compose_depends_on()` and `build_compose_service_dict()` from `core/module/module_service_spec.py`.
4. Update the tests:

| Test file | Change |
| --- | --- |
| `tests/unit/test_module_service_spec.py` | `:271`, `:276`: call `to_compose_service(output_spec.to_service_run())`, or assert on `to_service_run().args` / `.binds` directly. These test core behavior (args and mounts), so asserting on `ServiceRun` is the better fit. |
| `tests/unit/test_typed_paths.py` | `:232-240`: same approach; asserts that env reaches the service. |
| `tests/unit/test_generate_compose_property.py` | `_stub_spec()` (`:103-111`) stubs `generate_compose_service`. Stub `to_service_run` (return a `ServiceRun`) and `dependencies` (return `[]`) instead. |
| `tests/unit/test_service_output_characterization.py` | Compose cases switch to the new call; expected literals don't change. |

**Done when:** all tests pass; `module_service_spec.py` imports nothing Compose-related.

### Phase 4: docstrings and comments in `core/` (in scope, wording only)

Reword these to name no backend ("one service", "the run file", "when services are generated"):

- `core/module/module_service_spec.py:1-2`, `:108-110`, `:672` (comment naming `generate_compose`)
- `core/workflow.py:35`, `:86`
- `core/module/source_path.py:4`, `:12`
- `core/steps/sealevel_step.py:36`
- `core/experiment/experiment_plan.py:75`, `:90`, `:141`
- `core/experiment/experiment.py:110`

Also `application/execution_plan.py:49-53` (`_ExecutionPlan` docstring), which names `generate_compose_service()` and `_build_compose_depends_on()`. It is outside `core/`, but would be wrong after Phase 3.

`Workflow.facts_total_service_name_for_type()` (`core/workflow.py:85`) keeps its name; only the docstring changes. Service names are shared by both backends.

**Done when:** `grep -rniE "compose|apptainer|docker" src/facts_experiment_builder/core` prints nothing.

