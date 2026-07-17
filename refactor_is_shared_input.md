# Refactor: `is_shared_input()` off field-name heuristics, onto `mount.container_path`

## Current state

`is_shared_input(field_name)` in [path_utils.py:140-155](src/facts_experiment_builder/infra/path_utils.py#L140-L155) guesses shared-vs-module-specific by substring-matching the field name (`location`/`fingerprint`/`fp`). It's called once, inside `resolve_input_path()` ([path_utils.py:158-235](src/facts_experiment_builder/infra/path_utils.py#L158-L235)), which itself is called from two spots in `build_module_service_spec()` in [experiment_metadata_to_service_spec.py](src/facts_experiment_builder/adapters/experiment_metadata_to_service_spec.py#L228) (lines 228, 278).

The real, load-bearing signal already exists on every input arg-spec in the module registry YAMLs: `mount.container_path`, which is one of exactly two fixed strings across the whole registry — `/mnt/shared_in` or `/mnt/module_specific_in` (confirmed by direct inspection of the registry and of real generated compose output). By contrast `mount.volume` is inconsistently spelled (`"input"`, `"module_specific_in"`, `"module_specific_input"`, `"shared_input"` all appear) and unsuitable as a lookup key — so `container_path`, not `volume`, is the field to key off.

There's already a precedent for this exact pattern in `application/check_data.py`, which compares `mount.get("container_path")` against local constants `_SHARED_CONTAINER_PATH = "/mnt/shared_in"` / `_MODULE_SPECIFIC_CONTAINER_PATH = "/mnt/module_specific_in"`, and has a dead commented-out `# if is_shared_input(field_name):` line marking where it moved off the old approach.

One wrinkle: the metadata key used at the `resolve_input_path` call sites (e.g. `"location_file"`) is the **snake_case suffix of the arg-spec's `source`** (`source.split(".")[-1]`), not the arg-spec's `name` field (which is kebab-case and can differ in wording, e.g. `name: "rcmip-file"` vs `source: "...rcmip_fname"`). So looking up the right arg-spec dict for a given metadata key must reuse that same `source.split(".")[-1]` matching already used by the neighboring helpers `_dir_input_keys`/`_multiple_file_input_keys`.

## Detailed research findings

### 1. Module YAML location and `mount` shape examples

The registry lives at `/Users/emmamarshall/Desktop/facts_work/facts_v2/facts-module-registry` (sibling dir to `facts-experiment-builder`, a git repo). Confirmed via `src/facts_experiment_builder/infra/module_registry.py`'s `FileSystemModuleRegistry._yaml_path()` (`registry_path/module_name/{module_name_snake}_module.yaml`) and CLI defaults (`./facts-module-registry`, env var `FEB_MODULE_REGISTRY_DIR`) in `cli/setup_experiment_cli.py:158-161`, `cli/generate_compose_cli.py:92-94`, `cli/check_data_cli.py:56-58`, `cli/list_modules_cli.py:14-16`. It's cloned by `application/init_workspace.py` from `https://github.com/fact-sealevel/facts-module-registry.git`.

**Shared-input example** (`facts-module-registry/bamber19-icesheets/bamber19_icesheets_module.yaml:42-50`, a `location-file` top-level arg):
```yaml
- name: "location-file"
  source: "metadata.location-file"
  transform: "filename"
  mount:
    container_path: "/mnt/shared_in"
    volume: "input"          # <-- NOT "shared_input" (doesn't match volumes: dict key!)
```
Same file's fingerprint param (`:71-78`):
```yaml
- name: "fingerprint-dir"
  source: "module_inputs.fingerprint_params.fingerprint_dir"
  mount:
    volume: "input"           # <-- again "input", not "shared_input"
    container_path: "/mnt/shared_in"
```

**Module-specific example** (`bamber19_icesheets_module.yaml:92-98`, `slr-proj-mat-file`):
```yaml
- name: "slr-proj-mat-file"
  filename: "SLRProjections190726core_SEJ_full.mat"
  mount:
    volume: "module_specific_input"
    container_path: "/mnt/module_specific_in"
```

**`mount.volume` is unreliable / inconsistent across the registry.** Comparing every `mount.volume` value against that module's own `volumes:` dict keys shows **20 of 23 module YAMLs** have at least one input whose `mount.volume` value (commonly `"input"`) does not appear anywhere in that module's `volumes:` dict (which uses keys like `module_specific_input`/`shared_input`/`output`, or in `deconto21-ais` even `module_specific_in`/`shared_in`/`output`). Tally of all `mount.volume` string values across the registry:
```
  42  "input"
  23  "module_specific_in"
  18  "module_specific_input"
  87  "output"
  11  "shared_input"
```
So `volume` is spelled at least 4 different ways for what's conceptually 2-3 categories, and frequently doesn't match the `volumes:` dict key at all. **`mount.container_path` is fully consistent**, however: across every module YAML, shared inputs use exactly `/mnt/shared_in`, module-specific inputs use exactly `/mnt/module_specific_in`, and outputs use exactly `/mnt/out` (facts-total is the sole exception, using its own `/mnt/total_in`/`/mnt/total_out` — see open question below).

### 2. Docker-compose container mount paths

`full-v2-modules-docker-compose.yaml` (repo root) is a **legacy/outdated example** — it predates the current convention and uses distinct per-module mount names (`/mnt/fair_in`, `/mnt/ar5_glaciers_in`, `/mnt/ar5_glaciers_out`, `/mnt/sterodynamics_in`, etc.), not `/mnt/shared_in`/`/mnt/module_specific_in`.

A real, currently-generated compose file (`.history/experiments/global-emulandice2/experiment-compose_20260518113820.yaml:18-21`) confirms the actual current convention:
```yaml
volumes:
- /Users/.../data/module_specific_input_data/fair-temperature:/mnt/module_specific_in
- /Users/.../data/shared_input_data:/mnt/shared_in
- /Users/.../experiments/global-emulandice2/data/output:/mnt/out
```
So the fixed container paths `/mnt/shared_in` and `/mnt/module_specific_in` (plus `/mnt/out`) are the real, load-bearing convention, exactly matching `mount.container_path` values in the registry YAMLs.

### 3. Call sites of `is_shared_input` and `resolve_input_path`

Only one call site of each in `src/` (both in `src/facts_experiment_builder/infra/path_utils.py`):

- `is_shared_input(field_name: str) -> bool` (line 140-155) — takes a **bare field name string**, no access to spec dict.
- Called once, at line 205, inside `resolve_input_path(field_name, field_value, shared_input_data, module_specific_input_data, module_name="", context="")` (line 158-235) — this function also only receives `field_name` + `field_value` (a str or `{"value": ...}` dict) + base paths; it does **not** receive the input's full arg-spec dict (no `mount` available here).

`resolve_input_path` itself is called from exactly two places, both in `build_module_service_spec(metadata, module_name, known_module_names, module_definition: ModuleSchema, module_type=None)` in `experiment_metadata_to_service_spec.py`:
- Line 228 (inside the `multiple_file_input_keys` branch, iterating `module_inputs_section.items()`)
- Line 278 (main per-input branch)

`build_module_service_spec` has `module_definition: ModuleSchema` in scope at both call sites — it already iterates `module_definition.arguments.get("inputs", [])` elsewhere in the same function (e.g. `_dir_input_keys`, `_multiple_file_input_keys`, `module_definition.get_output_volume_input_keys()`). So the full arg-spec dict (including `mount`) is obtainable at the call site even though `resolve_input_path`'s current signature only takes `field_name`/`field_value`.

Also worth noting: `is_shared_input` also appears as a **stale, commented-out** call in `application/check_data.py:333` (`# if is_shared_input(field_name):`) — this module has *already* migrated away from field-name matching to reading `mount.container_path`/`mount.volume` directly, leaving the old call commented out as a trace of the prior approach.

### 4. `module_schema.py` and `arg_specs.py` — mount field schema

`src/facts_experiment_builder/core/module/arg_specs.py:12-17` defines `MountSpec` (Pydantic):
```python
class MountSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    container_path: str
    volume: str  # Optional[str] = None   <- comment suggests intent to make optional, but not actually done
    transform: Optional[str] = None
```
Both `container_path` and `volume` are **required** fields on `MountSpec` (no defaults) — despite the comment `# Optional[str] = None` next to `volume` suggesting someone considered relaxing it. `mount` itself is `Optional[MountSpec] = None` on every arg-spec model that has it: `TopLevelArgSpec` (line 29), `OptionArgSpec` (line 46), `InputArgSpec` (line 62), `OutputFileSpec` (line 92), `OtherOutputSpec` (line 105), `FingerprintParamSpec` (line 127). `ArgumentsSpec` (line 131-138) aggregates all these into `top_level`/`options`/`inputs`/`outputs`/`fingerprint_params` lists, and is instantiated for validation in `ModuleSchema.from_dict()` (`module_schema.py:134`, `ArgumentsSpec(**arguments)` — validates but the dict form, not the Pydantic objects, is what's stored on `ModuleSchema.arguments`).

`module_schema.py`'s `get_output_volume_input_keys()` (lines 97-115) is the one place in core that reads `mount.get("volume")`:
```python
def _output_volume_key(self) -> Optional[str]:
    """The key in self.volumes that maps to the shared output directory, or none."""
    for vol_key, spec in self.volumes.items():
        if isinstance(spec, dict) and "output_paths" in spec.get("host_path", ""):
            return vol_key
    return None

def get_output_volume_input_keys(self) -> set:
    output_vol = self._output_volume_key()
    ...
    for input_spec in self.arguments.get("inputs", []):
        mount = input_spec.get("mount", {})
        if isinstance(mount, dict) and mount.get("volume") == output_vol:
            ...
```
Note it doesn't hardcode `"output"` — it dynamically finds whichever `volumes:` key has `host_path` containing `"output_paths"` (i.e. `module_inputs.output_paths.output_dir`), then matches `mount.volume` against *that specific key string*. This works today only because output-mounted inputs consistently use `volume: "output"` and the `volumes:` dict's output entry is keyed `"output"` too — the one case where `mount.volume` and the `volumes:` dict key actually agree in practice.

### 5. `experiment_metadata_to_service_spec.py` / `compose_service_writer.py` / `module_service_spec.py` — volumes wiring

`compose_service_writer.py` (`build_compose_service_dict`) is a thin dict-builder — no mount/volume logic; it just assembles `{"image", "command", "volumes", "restart", "environment"?, "depends_on"?}` from already-resolved strings, and strips a leading `"main"` from `command[0]`.

The real volume-building logic is `ModuleServiceSpec._build_volumes()` in `core/module/module_service_spec.py:343-387`. It iterates `self.module_definition.volumes` (the YAML's top-level `volumes:` dict — e.g. keys `module_specific_input`/`shared_input`/`output`), and for each entry:
- Resolves `host_path` from `volume_spec["host_path"]` (a dotted source string like `module_inputs.input_paths.shared_input_dir`) via `self._resolve_value(...)` → `source_resolver.resolve_value()`.
- Takes `container_path` directly from that **same volumes-dict entry** (`volume_spec.get("container_path", "")`), **not** from any individual input's `mount.container_path`.
- Emits `f"{host_path}:{container_path}"`.
- Special-cases `volume_name == "output"`: uses the parent dir of `output_dir` as host path (so multiple modules can share one output-root volume mount, each writing to their own `/mnt/out/<module_name>/`).

So **volumes come only from `ModuleSchema.volumes` (top-level dict), never keyed by `mount.volume` on individual inputs.** The `mount` dict on an individual input/output is used purely in `_process_argument`/`_process_output_argument`/`_host_path_to_container` (lines 166-341) to build that **specific argument's CLI value** — i.e., turn a resolved host value into a container-path string for that one `--flag=value`, using `mount.container_path` (and `mount.transform`) directly, plus a check `mount.get("volume") == "output"` to detect the special case of output-relative inputs (climate file passed between modules). This confirms: `mount.volume` is only ever compared against the *literal string* `"output"` (or, in `module_schema.py`, against the dynamically-detected output volume key) — never used as a dict lookup key into `ModuleSchema.volumes`. Given the naming inconsistency documented in section 1, this "never dict-lookup, only equality-check" usage pattern is exactly what saves the current code from breaking on the inconsistent naming.

### Precedent already in the codebase for the proposed refactor

`application/check_data.py` has **already implemented** almost exactly what's being proposed, and offers a template:
- `_SHARED_CONTAINER_PATH = "/mnt/shared_in"` (line 293) and `_MODULE_SPECIFIC_CONTAINER_PATH = "/mnt/module_specific_in"` (line 147) are module-level constants.
- `plan_input_checks()` (line 177-208) branches on `inp.get("mount", {}).get("container_path") == "/mnt/shared_in"` to decide shared vs. module-specific, and on `inp.get("mount", {}).get("volume", "") == "output"` to detect inter-module deps — **not** on field name.
- `check_shared_data()` (line 296-359) explicitly has the old approach commented out: `# if is_shared_input(field_name):` replaced by `if container_path == "/mnt/shared_in": candidates.append(...)`.
- `plan_fp_checks()` (line 150-174) does the same for fingerprint params, using the module-specific constant as the discriminator (anything *not* module-specific-container-path is treated as shared).

This is strong evidence the team already validated (in `check_data.py`) that keying off `mount.container_path` string equality against the two known fixed container-path constants is more reliable than `mount.volume` (given the volume-name inconsistency documented above), and is more reliable than field-name substring matching (`is_shared_input`).

### Input-key-to-arg-spec lookup mechanics

The metadata key under `inputs:` in experiment-config.yaml is the last, snake_case segment of the arg-spec's `source` field — **not** the arg-spec's `name` field (kebab-case, sometimes a different word entirely). E.g. `fair-temperature`:
```yaml
- name: "rcmip-file"
  source: "module_inputs.inputs.rcmip_fname"
```
Metadata key is `rcmip_fname`, not `rcmip-file`. Confirmed by existing helpers in `experiment_metadata_to_service_spec.py` (lines 57-81):
```python
def _dir_input_keys(module_definition: Any) -> Set[str]:
    keys: Set[str] = set()
    for arg_spec in module_definition.arguments.get("inputs", []):
        if arg_spec.get("type") != "dir":
            continue
        source = arg_spec.get("source", "")
        if "." in source:
            keys.add(source.split(".")[-1])
    return keys


def _multiple_file_input_keys(module_definition: Any) -> Set[str]:
    keys: Set[str] = set()
    for arg_spec in module_definition.arguments.get("inputs", []):
        if not arg_spec.get("multiple", False):
            continue
        if not (arg_spec.get("mount") or arg_spec.get("type") == "file"):
            continue
        source = arg_spec.get("source", "")
        if "." in source:
            field = source.split(".")[-1]
            keys.add(field)
    return keys
```
Both derive the metadata key from `source.split(".")[-1]`, never from `name`. No existing helper in this file currently maps a metadata key back to its full arg-spec dict — a new one is needed (see plan step 4).

### Existing test coverage

`tests/unit/test_path_utils.py` (currently untracked, new) has three tests for `resolve_input_path`, all written against the **current** field-name-based behavior — e.g. `field_name="location_file"` implicitly resolving to the shared dir with no `mount` argument passed at all. These will need updating once `resolve_input_path` takes a `mount` parameter.

## Plan

1. **Centralize the container-path constants in `path_utils.py`.** Add `SHARED_INPUT_CONTAINER_PATH = "/mnt/shared_in"` and `MODULE_SPECIFIC_INPUT_CONTAINER_PATH = "/mnt/module_specific_in"` there (this module already owns input-path resolution). Update `check_data.py` to import these instead of keeping its own private duplicates (`_SHARED_CONTAINER_PATH`/`_MODULE_SPECIFIC_CONTAINER_PATH`) — same values, currently defined twice.

2. **Change `is_shared_input`'s signature** from `is_shared_input(field_name: str)` to `is_shared_input(mount: Optional[dict])`. Logic: return `True` if `mount.get("container_path") == SHARED_INPUT_CONTAINER_PATH`, `False` if it equals `MODULE_SPECIFIC_INPUT_CONTAINER_PATH`, and raise a `ValueError` (with field/module context) for anything else — missing mount, or an unrecognized container path — rather than silently guessing. Every input arg-spec in the registry already sets one of these two values, so requiring it is a real constraint, not a hypothetical one, and it'll surface authoring bugs in a module YAML instead of masking them.

3. **Change `resolve_input_path`'s signature** to take the mount dict for that field, e.g. `resolve_input_path(field_name, field_value, mount, shared_input_data, module_specific_input_data, module_name="", context="")`, replacing the internal `is_general = is_shared_input(field_name)` with `is_general = is_shared_input(mount)`. Keep `field_name` — it's still used for error messages and no other behavior.

4. **Wire the mount lookup through at the call sites.** In `experiment_metadata_to_service_spec.py`, add a small helper alongside `_dir_input_keys`/`_multiple_file_input_keys` (same file) that maps metadata key → arg-spec dict:
   ```python
   def _input_spec_by_key(module_definition) -> Dict[str, dict]:
       result = {}
       for arg_spec in module_definition.arguments.get("inputs", []):
           source = arg_spec.get("source", "")
           if "." in source:
               result[source.split(".")[-1]] = arg_spec
       return result
   ```
   Build it once in `build_module_service_spec` (next to where `output_root_relative_inputs`/`multiple_file_input_keys`/`dir_input_keys` are already built), then at both call sites (lines 228, 278) pass `input_spec_by_key.get(key, {}).get("mount")` as the new `mount` argument to `resolve_input_path`.

5. **Clean up `check_data.py`.** Delete the stale commented-out `# if is_shared_input(field_name):` trace at line 333, and confirm `plan_input_checks`/`plan_fp_checks`/`check_shared_data` keep using their existing (now-shared) `mount.container_path` comparisons — they were already doing the right thing, just with duplicated constants.

6. **Update tests.** `tests/unit/test_path_utils.py` currently calls `resolve_input_path` without a `mount` argument and relies on field-name substring matching. All three existing tests there need a `mount={"container_path": ...}` argument added and will need one more test for the "unrecognized/missing mount raises" case. Also grep `tests/unit/` and `tests/integration/` more broadly for any other direct callers of `is_shared_input`/`resolve_input_path` that pass bare field names before landing.

## Open question before implementing

facts-total uses different container path constants (`/mnt/total_in`/`/mnt/total_out` per the registry) — worth confirming whether facts-total's inputs ever flow through `resolve_input_path`/`is_shared_input` at all, or whether they're fully handled by the separate per-workflow service-generation path. If they do flow through, step 2's "raise on unrecognized path" would need a third recognized value (or a decision that facts-total inputs are never "shared" in this sense).
