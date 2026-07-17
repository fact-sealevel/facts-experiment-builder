# Architecture Review: facts_experiment_builder

Domain-driven design and layering review of the `facts_experiment_builder` codebase.

## Overall assessment

The **Adapters layer has been removed**: `adapters/` no longer exists in the tree.
`experiment_metadata_to_service_spec.py` (with `build_module_service_spec()`) moved
into `application/`, its former `adapter_utils.py` helpers (`get_required_field`,
`get_required_field_with_alternatives`, `get_experiment_paths`) were inlined directly
into that same file, and the dead `adapters/module_adapter.py` + its fully-commented
test were deleted outright. The codebase is now a three-layer
`CLI → Application → Core → Infra` split rather than the four-layer one CLAUDE.md
still documents (see Problem 7). This is a smaller, more honest architecture — the
"adapter" work here was translation-heavy, not really a distinct hexagonal boundary
with its own port — but the collapse also means `application/` now directly does
low-level dict/YAML shape-massaging that used to at least sit in its own file
labeled as translation. See Problem 2 for the practical effect of that merge.

The rest of the picture from the last review is largely unchanged: this is still
better described as a **schema-interpreter architecture with DDD vocabulary layered
on top** than textbook DDD — most "domain rules" live as string conventions in
module YAML (`source`, `mount.volume`, `transform`) dispatched at runtime rather than
as named domain concepts. Defensible for a plugin-schema system, still worth naming
honestly.

## Strengths

- **Ports done right**: `ModuleDefinitionSource` and `ExperimentStep`
  (`core/steps/base.py:9`) are real Protocols the application layer codes against,
  letting `FileSystemModuleRegistry` be swapped without touching `application/`.
- **Steps as polymorphic domain objects**: `ClimateStep`/`SealevelStep`/
  `TotalingStep`/`ExtremeSealevelStep` all implementing one protocol
  (`core/steps/factories.py`) replaces what could've been a pile of
  `if module_type == ...` branches with actual domain modeling of "a step in an
  experiment pipeline."
- **Value objects with parse-don't-validate**: `ExperimentName.parse()`
  (`core/experiment/name.py:24`) and `TypedPath` (`core/typed_path.py`) are exactly
  the shape good DDD value objects should be.
- **The clue/value bundle idiom** (`create_metadata_bundle`/`is_metadata_value`,
  `core/components/metadata_bundle.py`) is small, reused consistently across the
  application layer and the Jinja2 writer, and gives a clean way to represent "this
  field needs user input" without a separate type per field.
- **`list-modules` bug is fixed**: `cli/list_modules_cli.py` now correctly calls
  `module_registry.module_names()` and `module_registry._registry_path`, matching
  what `FileSystemModuleRegistry` (`infra/module_registry.py:62`) actually exposes.
  (Previously called nonexistent methods and raised `AttributeError` at runtime —
  see prior review.) There is still no `test_list_modules_cli.py`, so this class of
  drift remains uncaught by tests even though the current code is correct.
- **`adapters/module_adapter.py` dead code is gone**: the fully-commented-out file
  and its fully-commented-out test (`tests/unit/test_module_adapter.py`) were
  deleted rather than left as false surface area.

## Problems worth fixing

### 1. Core depends on Infra — inverts the architecture's own stated dependency rule

`ModuleServiceSpec` (`core/module/module_service_spec.py:8-14`) imports
`ModuleInputPaths`/`ModuleOutputPaths` from `infra.path_utils` and
`build_compose_service_dict` from `infra.compose_service_writer`, and its
`generate_compose_service()` directly builds Docker Compose shape (`/mnt/...`
container paths, volume strings, `depends_on` dicts). That's infrastructure/
deployment-shape knowledge sitting in what's labeled "Core (domain)." In a real
layered split, Core would emit a neutral resolved-value object and an infra-side
builder would turn it into compose YAML shape — right now the direction of
dependency is backwards from CLAUDE.md's own diagram. Unchanged since the last
review.

### 2. Former "adapter" logic is now application-layer logic, and the merge grew it

`build_module_service_spec()` lives in
`application/experiment_metadata_to_service_spec.py:222-576` — up from 440 lines
to nearly 580, because the reorg folded the old `adapters/adapter_utils.py` helpers
(`get_required_field`, `get_required_field_with_alternatives`,
`get_experiment_paths`, both now at `experiment_metadata_to_service_spec.py:54-188`)
directly into the same file rather than keeping them as a separate translation
layer. It's still doing path resolution, `TypedPath` classification, facts-total/ESL
per-workflow special-casing, and output-container-base logic all in one place — and
now it's not even labeled as a distinct "adapter" concern anymore, it's just
`application/`, which per CLAUDE.md is supposed to be orchestration ("5-step flow"
style), not translation. Removing the adapters layer didn't remove the translation
work, it just moved it one level up and merged it with orchestration code. Still the
single highest-value target for decomposition — arguably more so now that its home
layer no longer signals what kind of logic it contains.

### 3. Dead code left in the tree, some of it internally inconsistent

- `core/workspace/workspace.py` (`WorkspaceConfig`) + `infra/workspace_loader.py`
  are unreferenced by any CLI path — superseded by `application/init_workspace.py`,
  which reimplements the same "workspace init" concept differently (writes a YAML
  marker file, `.facts-workspace`) while the dead version reads a workspace config
  as TOML via `tomllib.load`. These two would never interoperate if both were wired
  up. (Per project memory, `core/workspace/` is already understood to be
  out-of-scope for the current refactor — this is a reminder it's still sitting in
  the tree, not a new finding.)
- `core/total_checker.py` is an empty file (0 bytes), unreferenced anywhere.
- `infra/experiment_manager.py` is superseded by `FileSystemExperimentStorage`
  (`infra/experiment_storage.py`) and is only kept alive by its own test
  (`tests/unit/test_experiment_manager.py`).

### 4. Duplicate value objects

`ScenarioConfig` is defined twice — `core/module/module_schema.py:199` and
`core/module/module_service_spec.py:26` — the second copy appears entirely unused
(transforms read `module_definition.extra` directly instead). Unchanged.

### 5. Two independent readers of the same experiment-config.yaml shape

`FactsExperiment.from_metadata_dict()` (`core/experiment/facts_experiment.py:181`)
and `generate_compose.py`'s private helpers (`application/generate_compose.py:84`)
both parse the manifest/module-sections/paths independently. They still disagree in
one place: `from_metadata_dict` infers `esl_modules`
(`core/experiment/facts_experiment.py:254-259`) via a
`startswith("extremesealevel-")` backward-compat fallback that
`application/generate_compose.py`'s manifest extraction does not replicate — a
config shape that trips one and not the other remains a real drift risk. Unchanged.

### 6. CLAUDE.md has drifted further from the code

The doc still describes a four-layer `CLI → Application → Adapters → Core →
Infrastructure → Resources` split with an `adapters/` directory containing
`experiment_metadata_to_service_spec.py`, `compose_service_writer.py`,
`module_adapter.py`, and `adapter_utils.py`. None of that directory exists anymore:
`experiment_metadata_to_service_spec.py` is in `application/`,
`compose_service_writer.py` is in `infra/`, `module_adapter.py` is deleted, and
`adapter_utils.py`'s functions are inlined into
`application/experiment_metadata_to_service_spec.py`. The doc's `resources/configs/`
section is also stale — bundled module YAMLs are no longer used; module definitions
now come from an external `facts-module-registry/` (per project memory), and
`resources/` on disk today only holds `resources/clues/top_level_param_clues.yaml`.
Separately, `core/steps/`, `core/workspace/`, `arg_specs.py`,
`module_definition_source.py`, `experiment_skeleton.py`, `name.py`,
`total_checker.py` still aren't mentioned in the doc. Worth a full doc pass — the
gap between documented and actual layering is now larger than before this reorg,
not smaller.

## Priority order

1. Update CLAUDE.md's architecture section to match the actual `CLI → Application →
   Core → Infra` layering and the `facts-module-registry`-based resources story —
   the doc is currently actively misleading about a layer (`adapters/`) that no
   longer exists.
2. Delete the remaining dead files (`core/workspace/*`, `infra/workspace_loader.py`,
   `core/total_checker.py`, `infra/experiment_manager.py` + its test) rather than
   let them keep implying alternate designs that were abandoned.
3. Decide intentionally whether Core is allowed to know about compose/infra shape —
   if not, carve compose-dict-building out of `ModuleServiceSpec` into infra.
4. Split `build_module_service_spec()` — it's the piece most likely to keep growing
   special cases, and it's now less clearly scoped than before since it lost its
   dedicated "adapter" home.
