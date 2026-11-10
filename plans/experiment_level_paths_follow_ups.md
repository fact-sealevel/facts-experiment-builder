# Follow-ups after `experiment_level_paths` (#130)

#130 resolves the experiment-level path keys (`shared-input-data`,
`module-specific-input-data`, `output-data-location`,
`experiment-specific-input-data`) once per experiment into `ExperimentDataPaths`,
renames `resolve_experiment_paths()` to `resolve_module_paths()`, and passes
`data_paths` explicitly from `generate_compose()` down to
`build_module_service_spec()`.

This doc plans the follow-up work found while scoping and reviewing #130: five
small PRs on `main`, plus a separate track for the Apptainer branch. Line numbers
refer to `main` at `5cc0c0c` and may drift.

| PR | Branch | Status |
|---|---|---|
| 1. Remove duplicate `core/experiment/paths.py` | `experiment_name_validation` | Committed (`bb7f0e6`), PR not yet opened |
| 2. Experiment dir creation at setup | `setup_experiment_dir` | Committed (`dabfa03`..`a82f345`), PR not yet opened |
| 3. Single reader for experiment-level path keys | `single_path_key_reader` | Implemented, uncommitted |
| 4. Build `TopLevelParams` once per experiment (optional) | — | Not started; decision open |
| 5. Fix `generate-compose --custom-compose-path` | — | Not started |
| Apptainer track | `add_apptainer_command` | WIP (`637acb1`), needs rebase onto `main` |

---

## PR 1: Remove duplicate `core/experiment/paths.py`

**Status:** done on `experiment_name_validation` (`bb7f0e6`).

**Findings**
- `core/experiment/paths.py` held a second copy of `InvalidExperimentNameError` and
  `ExperimentName`, plus an unused `ExperimentPathContainer`. Nothing in `src/`,
  `tests/` or `docs/` imported it.
- The unused copy validated in `__post_init__` (with `fullmatch`). The live copy in
  `core/experiment/name.py` validated only in `parse()`, so direct construction
  accepted invalid values.
- `parse()` used `_VALID.match(...)`. Because `$` also matches before a trailing
  newline, `"a\n/b"` was accepted with `parent=Path("a\n")`.
- `ExperimentName` had no tests.

**Changes**
- `name.py`: a single `_is_valid_part()` rule (`fullmatch` against
  `[A-Za-z0-9._-]`, never `.` or `..`) applied in `__post_init__` to the name and
  every parent component; absolute or empty parents are rejected. `parse()` only
  splits the input and re-raises with the raw input, so error messages are unchanged.
- Deleted `core/experiment/paths.py`.
- Added `tests/unit/test_experiment_name_property.py` (14 Hypothesis property
  tests).

**Behavior change (verified against the old code)**
- `parse()`: of 31 edge-case inputs, only `"a\n/b"` changed (now rejected). All
  others give the same result and the same error `raw_name`.
- Direct construction now raises for invalid values. Nothing in the repo constructs
  `ExperimentName` directly.
- Against the old `name.py`, the new tests fail on exactly those 3 behaviors and
  pass the other 11.

---

## PR 2: Experiment directory creation at setup

**Branch:** `setup_experiment_dir` (from `main`, `5cc0c0c`).

**Status:** done (`dabfa03`..`a82f345`). Scope grew during implementation to also
restore two 0.5.0 checks (see "Added during implementation" below).

**Findings.** `make_output_dir()` (`io/paths.py` L50-52,
`output_dir.mkdir(parents=True)`, called at `application/setup_experiment.py` L85)
does three jobs implicitly:
1. **Creates the experiment directory.** `write_config_jinja2()` opens
   `config_path` without creating parents (`io/write_config.py` L249), so writing
   the config depends on this. `generate_compose()` also asserts the experiment
   directory exists (`application/generate_compose.py` L358).
2. **Creates a default `output/` directory** that isn't tied to the config. If a
   user edits `output-data-location`, `output/` is left behind, empty. At generate
   time, `ensure_module_output_dir()` (`io/module_dirs.py`, `os.makedirs`) already
   creates the directories actually used, including parents.
3. **Is the only "experiment already exists" guard.** No `exist_ok`, so re-running
   setup raises a raw `FileExistsError` traceback. `ExperimentAlreadyExistsError`
   (`core/experiment/exceptions.py`) is defined but never raised, although
   `docs/MIGRATION.md` L105 and the `setup-experiment` help text
   (`cli/setup_experiment_cli.py` L201) describe it to users.

The skeleton also hardcodes the default output path as
`Path(experiment_path, "output")` (`core/experiment/skeleton.py` L345),
independently of `ExperimentPaths.output_dir` (`io/paths.py` L38-40). They agree
only because both hardcode `"output"`.

Nothing checks that `output-data-location` exists: config loading only checks it
is present and a string, and `check-data` only checks input directories.

**Decisions**
- An experiment "exists" if its `experiment-config.yaml` exists.
- Setup no longer creates the default `output/` directory.

**Changes**
1. Replace `make_output_dir()` with a function that creates `experiment_dir`
   (`exist_ok=True`) and raises `ExperimentAlreadyExistsError` if
   `config_path` exists.
2. The skeleton takes its default `output-data-location` from
   `ExperimentPaths.output_dir` instead of hardcoding `"output"`. Setup passes
   `output_dir` instead of `experiment_path` (`application/setup_experiment.py`
   L211). The value written to the config is unchanged.
3. Check docs for any statement that `output/` exists right after setup, and
   update them.
4. Tests:
   - running setup twice raises `ExperimentAlreadyExistsError`
   - setup succeeds when the experiment directory exists but has no config
   - the config is written into a newly created directory
   - the default `output-data-location` equals `ExperimentPaths.output_dir`
   - setup does not create `output/`

**Risk:** user-visible change in how "already exists" is reported (a clear error
instead of a traceback), and a slightly different trigger (config file rather than
`output/`). The default `output-data-location` doesn't exist until the first
`generate-compose`.

**Added during implementation**
- **Parent directories are never created.** `make_output_dir()`'s
  `mkdir(parents=True)` silently created missing parents of `--experiment-name`
  (e.g. `funky_experiments/` for `funky_experiments/my_exp`). v0.5.0 used
  `mkdir(parents=False, exist_ok=False)` and raised `ExperimentParentNotFoundError`.
  History: #102 replaced that with `make_output_dir()` (`parents=True`) in
  `io/experiment_storage.py`; #108 moved `make_output_dir()` unchanged to
  `io/paths.py`. Restored: `create_experiment_dir()` uses
  `mkdir(parents=False, exist_ok=True)`, and a missing parent raises
  `ExperimentParentNotFoundError`.
- **Workspace containment check restored** (from v0.5.0): an experiment dir that
  resolves outside the workspace (e.g. via a symlinked parent) raises
  `ExperimentOutsideWorkspaceError`.
- All three setup errors subclass a new `ExperimentSetupError`; the CLI catches it,
  prints a one-line error and exits 1.
- Fixed the "Created experiment directory at:" message, which printed an
  `ExperimentPaths` repr instead of the path.

**As implemented:** `prepare_experiment_setup()` runs `check_experiment_location()`
and `check_experiment_does_not_exist()` before any prompts and creates nothing;
`finalize_experiment_setup()` re-checks and calls `create_experiment_dir()` (which
re-runs the location check) right before writing the config. Tests:
`tests/unit/test_setup_experiment_dir.py` (24); two tests in
`test_setup_experiment.py` now create their parent dir.

---

## PR 3: Remove unused path normalization in `FactsExperiment.from_metadata_dict()`

**Branch:** `single_path_key_reader` (from `main`, `5cc0c0c`). **Status:** implemented.

**Decisions**
- Option 1: keep `get_experiment_paths()`'s strict rules and document them.
- Remove the alternative key spellings (`shared_input_data`,
  `module_specific_input_data`, `output_data_location`, `output-path`,
  `output_path`). Verified that no FEB template or shipped example config in any
  release wrote them at the top level, and since 0.6.0 every usable config is
  written by the current template (`module_schemas` required).

**As implemented**
- `get_experiment_paths()` reads only the template's key names via a small
  `_get_required_path()` helper; `get_required_field_with_alternatives()` removed.
  Rules documented in its docstring; `experiment-specific-input-data` rules
  documented on `resolve_experiment_data_paths()`.
- `FactsExperiment.from_metadata_dict()` no longer normalizes paths (`paths={}`);
  `PATH_KEYS_ALTERNATIVES` removed; path keys excluded from `extra` via
  `PATH_KEYS_PRIMARY`.
- Tests: alternative spellings now count as missing; removed the redundant
  None-doesn't-fall-back test; added a list case for
  `experiment-specific-input-data`; new `test_experiment_from_metadata.py`.
- Compose output for `my_facts_experiment` unchanged.

The original analysis follows.

**Findings**
- `FactsExperiment` is built in two places:
  - **At setup** by `experiment_skeleton_to_facts_experiment()`
    (`core/experiment/skeleton.py` L365). There `paths` holds `{clue, value}`
    bundles that `core/experiment/experiment_config.py` (L107-122, L229) uses to
    **write** the config. This use is legitimate.
  - **At generate time** by `from_metadata_dict()`
    (`core/experiment/experiment.py` L225-241), which normalizes the path keys a
    second way.
- At generate time, `plan.experiment` is only read for `.projection_scale`
  (`application/execution_plan.py` L195, L324, L328). Its `.paths` is computed and
  never read. No tests use `from_metadata_dict()` or `.paths`.
- The two normalizers behave differently:

| Case | `get_experiment_paths()` | `from_metadata_dict()` |
|---|---|---|
| Primary key present but `None`, alternative set | raises (checks key presence only) | falls back to the alternative |
| Value is `{"value": "..."}` | raises (not a `str`) | unwraps it |
| Value is a `{"clue": ...}` bundle | raises | keeps the dict |

**Changes**
1. Remove the path normalization block from `from_metadata_dict()` and pass
   `paths={}` (or make `paths` optional). Keep `PATH_KEYS_*` in `_STRUCTURAL_KEYS`
   so path keys aren't treated as top-level params.
2. **Decision open:** keep `get_experiment_paths()`'s current rules (and document
   them on `ExperimentDataPaths`), or make them consistent (`None`-primary falls
   back; `{"value": ...}` unwrapped for all keys, as `experiment-specific-input-data`
   already is). Making them consistent is a behavior change: do it in its own
   commit and update the two characterization tests in
   `tests/unit/test_module_paths_characterization.py` that pin the current
   behavior.
3. Tests: `from_metadata_dict()` on a loaded config still yields the same
   `projection_scale`, manifest and steps.

**Risk:** low for change 1 (removes unread code). Change 2 depends on the decision.

---

## PR 4 (optional): Build `TopLevelParams` once per experiment

**Findings (verified).** `TopLevelParams.from_config(metadata)`
(`core/components/top_level_params.py` L22-37) reads only its 8 fields (kebab- or
snake_case keys). It's called once per module in `build_module_service_spec()`
(`application/module_service_spec_factory.py`). The per-workflow `metadata_copy`
in `execution_plan.py` only adds service-section keys (`facts-total-<wf>-<type>`,
`<esl-module>-<wf>`) that can't collide with those fields, so the result is
identical for every module.

**Changes:** build it once in `generate_compose()` next to `data_paths` and pass it
through to `build_module_service_spec()`, the same way #130 did. Verify with the
before/after compose diff.

**Value:** consistency only, no bug fixed. Adds another arg along the same chain.
**Decision open:** do it (optionally bundling `data_paths` and `top_level_params`
into one experiment-context object), or drop it.

---

## PR 5: Fix `generate-compose --custom-compose-path`

**Findings**
- `cli/generate_compose_cli.py` L62-66 declares the option as `click.Path()`
  without `path_type=Path`, so the value is a `str` and
  `application/generate_compose.py` L351 fails on `.resolve()`
  (`AttributeError: 'str' object has no attribute 'resolve'`).
- After writing the file, the CLI prints `compose_path.relative_to(Path.cwd())`
  (`cli/generate_compose_cli.py` L142), which raises `ValueError` when the output
  path isn't under the current directory (likely with a custom path, or when
  `--workspace-dir` isn't the cwd).
- No test passes `--custom-compose-path`.
- `generate-apptainer`'s `--custom-script-path` already uses `path_type=Path`.

**Changes**
1. `type=click.Path(path_type=Path, resolve_path=True)`.
2. Print a relative path only when it can be computed; otherwise print the
   absolute path.
3. CLI tests: custom path inside and outside the cwd.

**Risk:** low. This is a bug users can hit in 0.6.0, so it belongs under "Fixed"
in the changelog.

---

## Apptainer track (`add_apptainer_command`)

`add_apptainer_command` (WIP `637acb1`) is based on `ead3e7f`; `main` now also has
#129 and #130.

1. **Rebase onto `main`.** Expect a conflict in `core/module/module_service_spec.py`:
   #129 renamed params in `generate_compose_service()`, and the branch adds
   `generate_apptainer_service()` right after it. `generate_apptainer.py` calls
   `_build_module_specs()` and `build_experiment_execution_plan()` without
   `data_paths`, so those calls must be updated.
2. **Separate Apptainer output root.** Build `data_paths` once, then
   `dataclasses.replace(data_paths, output_data_location=<apptainer root>)` before
   building specs. **Decision open:** where the root comes from: a new config key,
   or an `ExperimentPaths` default plus a `--output-dir` CLI flag.
3. **Remove direct metadata reads.**
   - Add `ModuleServiceSpec.host_output_paths()` (host paths of outputs on the
     shared output volume, built from `output_paths.output_dir`) and use it for the
     Stage 2 climate wait files, instead of re-parsing `_build_command_args()` and
     swapping `/mnt/out` for `metadata["output-data-location"]`
     (`generate_apptainer.py` L59-89, L99).
   - Remove the metadata reads in `write_apptainer.py` (L21-23), or take the values
     from `data_paths`. `OUTPUT_DIR` / `SHARED_IN` / `MODULE_IN` are unused in the
     template today.
4. **Move per-service data onto `ApptainerServiceSpec`** (`output_dir`, `registry`,
   `host_outputs`), so `generate_apptainer` reads `ModuleServiceSpec` only to
   choose stages.
5. **Correctness bugs.**
   - The leading `main` arg isn't stripped for Apptainer (Compose strips it in
     `build_compose_service_dict`). Best fixed once in `_build_command_args()` for
     both.
   - `envvar` inputs are dropped (no environment is passed to `apptainer run`;
     use `--env`).
   - `standalone_esl_specs` get `mkdir`'d but are never run in the script.
6. **Generating on macOS to run in Lima.** `ensure_module_output_dir()` creates
   output dirs at spec-build time, which fails or creates stray directories if the
   Apptainer output root is a VM-only path. Decide whether Apptainer generation
   should skip it and rely on the script's own `mkdir -p`.
7. **Optional.** Express template binds through top-level variables
   (`${OUTPUT_DIR}` etc.) using a structured bind representation rather than
   string-prefix substitution.

---

## Changelog entries (PRs 1–3)

Drafts for `## [Unreleased]` in `CHANGELOG.md`. Replace `#XXX` with each PR's
number once opened.

### PR 1: `ExperimentName` validation

```markdown
### Changed
- `ExperimentName` now validates on construction (not only in `parse()`), using one rule for the name and each parent component; removed the unused duplicate `core.experiment.paths` module ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))

### Fixed
- `--experiment-name` values with a newline at the end of a parent directory component (e.g. `"a\n/b"`) were accepted; they now raise `InvalidExperimentNameError` ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))
```

### PR 2: Experiment directory creation at setup

```markdown
### Changed
- An experiment is considered to exist if its `experiment-config.yaml` exists. `setup-experiment` no longer creates an empty `output/` directory, and creates the experiment directory only after all checks and workflow prompts. `io.paths.make_output_dir()` is replaced by `check_experiment_does_not_exist()`, `check_experiment_location()` and `create_experiment_dir()` ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))

### Fixed
- `setup-experiment` created missing parent directories of `--experiment-name` (regression in 0.6.0); it now raises `ExperimentParentNotFoundError`, and rejects experiment paths that resolve outside the workspace with `ExperimentOutsideWorkspaceError` ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))
- Re-running `setup-experiment` for an existing experiment raised a raw `FileExistsError`; it now raises `ExperimentAlreadyExistsError` with a clear message, as documented in `docs/MIGRATION.md` ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))
- `setup-experiment` printed an `ExperimentPaths` object instead of the experiment directory path in its "Created experiment directory" message ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))
```

Open question: whether to mark the parent-directory fix as **Breaking** (0.6.0 users
who relied on parents being created must now create them first).

### PR 3: Single reader for experiment-level path keys

```markdown
### Changed
- **Breaking:** Experiment-level path keys in `experiment-config.yaml` are only read under the names written by `setup-experiment` (`shared-input-data`, `module-specific-input-data`, `output-data-location`); the alternative spellings `shared_input_data`, `module_specific_input_data`, `output_data_location`, `output-path` and `output_path` are no longer accepted. Configs written by `setup-experiment` are unaffected ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))
- `FactsExperiment.from_metadata_dict()` no longer normalizes path keys; experiment-level paths are read only by `get_experiment_paths()` / `resolve_experiment_data_paths()`, whose rules are now documented ([PR #XXX](https://github.com/fact-sealevel/facts-experiment-builder/pull/XXX), [@e-marshall](https://github.com/e-marshall))
```

---

## Other findings (not yet planned)

- Five pre-existing pyright errors in `application/generate_compose.py` and
  `application/execution_plan.py`. Two could hide real bugs:
  `plan.climate_module_name` may be `None` where `.upper()` is called, and
  `generate_compose()` is annotated to return `dict[str, Any]` but returns
  `PrepareComposeOutput`.

### Config writer: lists in module sections / `module_schemas` don't round-trip

Found 2026-10-07 while writing `tests/unit/test_scenario_passthrough.py` (branch
`remove_ssplws_transform`). Both bugs are in `format_module_value()`,
`io/write_config.py` L97-101 (the list branch), which writes module sections and the
frozen `module_schemas` into `experiment-config.yaml`:

```python
elif isinstance(value, list):
    lines.append(f"{indent_str}{key}:")
    for item in value:
        lines.append(f"{indent_str}  - {item}")
```

1. **Empty lists are written as blank values.** `[]` is written as `key:` with no
   items, which YAML loads as `null`. Reproduced: `options=[]` → `options:` →
   `{'options': None}`. On load, `ModuleSchema.from_dict()` passes it to
   `ArgumentsSpec`, which rejects `None`, so `generate-compose` fails. The dict branch
   just above already handles the empty case (`key: {}`); the list branch doesn't.
   `ModuleSchema.to_dict()` uses `model_dump(exclude_unset=True)`, so any list the
   module YAML explicitly sets (even empty) is written.
2. **`None` inside list items becomes the string `'None'`.** Items are written with
   `str(item)`, i.e. Python repr (`{'name': 'x', 'optional': True, 'help': None}`).
   YAML parses most of that correctly, but `None` is not YAML null. Reproduced:
   `'help': None` reloads as `'help': 'None'`. This silently changes the frozen schema
   rather than raising.

**Impact today:** none on real experiments. Neither registry's module YAMLs contain
explicit empty lists or `null`s, and `BC_my_facts_experiment` /
`my_facts_experiment` have no `: None` in `module_schemas`. Triggered by any module
YAML with e.g. `options: []`, `depends_on: []` or an explicit `null` argument field,
and by test schemas built with `tests/unit/helpers.make_schema()`'s default
arguments (empty lists).

**Fix:** in the list branch, write `key: []` for an empty list, and write items as real
YAML instead of `str(item)` (e.g. `yaml.safe_dump(item, default_flow_style=True)` or
`json.dumps(item)`, both valid flow-style YAML). Newly written configs would then show
JSON-style `{"name": ...}` instead of Python-style `{'name': ...}`; loaded values are
unchanged except the `None` case.

**Tests:** a round-trip test, `ModuleSchema.to_dict()` → writer → `yaml.safe_load` →
`ModuleSchema.from_dict()`, should return an equal schema, covering an empty list and
a `None` field. Once fixed, remove the `make_schema("facts-total", arguments={})`
workaround (and its comment) in `tests/unit/test_scenario_passthrough.py`.

**Where:** a separate branch from `main`; unrelated to the ssp-landwaterstorage work.
