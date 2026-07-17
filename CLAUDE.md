# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```shell
uv sync
```

**Run all tests:**
```shell
uv run pytest
```

**Run a single test:**
```shell
uv run pytest tests/test_generate_compose.py::test_module_requires_climate_file_false_when_key_false
```

**Lint:**
```shell
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

**Run CLI commands (development):**
```shell
uv run feb init
uv run feb setup-experiment --experiment-name <name> --climate-step fair-temperature --sealevel-step <modules> --extremesealevel-step extremesealevel-pointsoverthreshold
uv run feb generate-compose --experiment-name <name>
```
`feb` is the top-level Click group (`cli/__init__.py`); each subcommand is also installed as its own standalone script (`setup-experiment`, `generate-compose`, `list-modules`, `check-data`, `init-workspace`) per `pyproject.toml`.

## Architecture

This is a CLI tool for configuring and generating Docker Compose files for FACTS v2 sea-level rise experiments. The codebase follows a layered architecture:

```
CLI → Application → Core (domain) → Infrastructure
```

There is no separate Adapters layer — it was folded into `application/` (see below) —
and no bundled Resources layer either: module definitions come from an external
`facts-module-registry/` git repo (cloned by `feb init`), not from YAMLs shipped in
this package.

**Entry / CLI** (`src/facts_experiment_builder/cli/`): Click commands, grouped under
the `feb` entry point (`cli/__init__.py`): `init`, `setup-experiment`,
`generate-compose`, `list-modules`, `check-data`. All assume they are run from a
project root that has an `experiments/` subdirectory (created by `feb init`, or
via `--root`). Every command that touches module definitions takes a
`--module-registry` option (default `./facts-module-registry`, env var
`FEB_MODULE_REGISTRY_DIR`) pointing at the external registry clone. The
setup-experiment CLI handles interactive workflow definition for the sealevel step.

**Application** (`application/`): Orchestrates use cases, and — since the adapters
layer was removed — also does the metadata/YAML translation work that used to live
in `adapters/`.
- `setup_experiment.py`: builds a `FactsExperiment` from CLI args + module schemas
  (`prepare_experiment_setup()`), then writes `experiment-config.yaml`
  (`finalize_experiment_setup()`).
- `experiment_metadata_to_service_spec.py`: `build_module_service_spec()` — loads
  module YAML, resolves experiment paths, resolves typed inputs/outputs, builds
  `ModuleServiceSpecComponents` and `ModuleServiceSpec`. Handles special cases:
  ipccar5 shared dir, ESL per-workflow services, output-relative inputs. Also holds
  the field-extraction helpers formerly in `adapters/adapter_utils.py`
  (`get_required_field()`, `get_required_field_with_alternatives()`,
  `get_experiment_paths()`).
- `generate_compose.py`: Loads a completed `experiment-config.yaml`, builds
  `FactsExperiment`, creates a `ModuleServiceSpec` per module (temperature,
  sealevel, framework, ESL), and produces `experiment-compose.yaml`. Validates
  climate file inputs when temperature module is `NONE`. facts-total and ESL
  modules generate per-workflow service instances (e.g. `facts-total-wf1-global`).
- `check_data.py`: plans and executes checks for whether required input files exist
  in the module-registry's declared locations, used by the `check-data` CLI.
- `init_workspace.py`: idempotent steps for `feb init` — create `experiments/`,
  clone `facts-module-registry/`, add it to `.gitignore`, write the
  `.facts-workspace` marker file.
- `experiment_helpers.py`: `hydrate_experiment()` builds the four `Step` objects
  (climate/sealevel/totaling/ESL) from an `ExperimentSkeleton` + module schemas;
  `experiment_skeleton_to_facts_experiment()` assembles the full `FactsExperiment`.

**Core** (`core/`):
- `FactsExperiment` (`core/experiment/facts_experiment.py`): In-memory representation of `experiment-config.yaml`. Two constructors: `from_metadata_dict()` (parse loaded YAML) and `create_new_experiment_obj()` (build from CLI inputs with injected helpers). `merge_defaults_for_module()` merges a defaults YAML into the module section with snake/kebab-case flexibility.
- `ModuleExperimentSpec` (`core/module/module_experiment_spec.py`): In-memory representation of one module's section in experiment-config.yaml. Constructors: `from_module_schema()` (builds initial spec with clue/value placeholders) and `from_dict()` (parses a loaded metadata dict). `merge_defaults()` merges a defaults YAML in place. `is_configured()` returns True if no unfilled clue/value bundles remain. `to_dict()` serializes back to the raw dict shape used in YAML.
- `ModuleSchema` (`core/module/module_schema.py`): Dataclass for a module YAML. Fields: `module_name`, `container_image`, `arguments` (dict with keys `top_level`, `options`, `inputs`, `outputs`, `fingerprint_params`), `volumes`, `depends_on`, `command`, `uses_climate_file`, `extra`.
- `ModuleServiceSpec` (`core/module/module_service_spec.py`): Fully resolved spec for one Docker Compose service. `generate_compose_service()` orchestrates `_build_command_args()`, `_build_volumes()`, `_build_depends_on()`. Arguments are processed in YAML order: top_level → fingerprint_params → options → inputs → outputs. Automatically adds depends_on for temperature service when `uses_climate_file` is true.
- `Workflow` (`core/workflow/workflow.py`): Frozen dataclass (`name` + `module_names`). Provides service naming (`facts_total_service_name_for_type`) and output filename conventions. `workflows_from_metadata()` / `workflows_to_metadata()` handle serialization.
- `transforms.py`: `scenario_name_ssp_landwaterstorage()` maps scenario names for the ssp-landwaterstorage module using a bundled config YAML.
- `source_resolver.py`: Resolves dot-separated source strings (e.g. `metadata.pipeline-id`, `module_inputs.outputs.foo`) against a context dict/object, with snake/kebab-case fallback.
- `typed_path.py`: `TypedPath` with `HostPath`/`ContainerPath` constructors — used so the compose builder knows whether to rewrite a path to a container path or use it as-is.
- `components/metadata_bundle.py`: `create_metadata_bundle(clue, value)` and `is_metadata_value()` — extracted here from the application layer so core objects can use them directly.

**Infrastructure** (`infra/`):
- `module_registry.py`: `FileSystemModuleRegistry` — resolves a module name to
  `{registry_path}/{module_name}/{module_name_snake}_module.yaml` in the external
  `facts-module-registry/` clone, loads it into a `ModuleSchema`, and caches it.
  Also exposes `module_names()` (used by `list-modules`) and `version()` (registry's
  git short hash).
- `path_utils.py`: Expands `~` and env vars (`expand_path`), routes inputs to general vs module-specific base paths (`resolve_input_path`, `is_shared_input`), resolves output paths (`resolve_output_path`).
- `experiment_storage.py`: `FileSystemExperimentStorage` — creates the experiment directory structure (`experiments/<name>/`, `data/output/`, per-module subdirs) and resolves experiment metadata/compose file paths. This is the live replacement for the older `experiment_loader.py`/`experiment_manager.py` (the latter is now dead code, kept alive only by its own test — see below).
- `write_experiment_metadata.py`: Jinja2 template (`YAML_TEMPLATE`) for `experiment-config.yaml`. Clue/value dicts (created by `create_metadata_bundle`) render as YAML comments with optional placeholder values, guiding the user to fill in required fields.
- `write_compose.py`: Serializes compose dict with `yaml.dump()`, then post-processes the string (`format_compose_yaml`) to enforce exact indentation and add double-quotes around command args.
- `compose_service_writer.py`: Converts a `ModuleServiceSpec`'s resolved command/volumes/depends_on into a Docker Compose service dict. Strips `"main"` from `command[0]` if present.

**Dead code still in the tree** (not part of the live architecture, not deleted yet): `core/workspace/workspace.py` + `infra/workspace_loader.py` (superseded by `application/init_workspace.py`, which uses a different, incompatible marker-file format), `core/total_checker.py` (empty file), `infra/experiment_manager.py` (superseded by `infra/experiment_storage.py`, referenced only by its own test).

**Resources** (`resources/`): No longer holds module definitions — those come from the external `facts-module-registry/` git repo (see `infra/module_registry.py` and the `--module-registry` CLI option above), cloned via `feb init`. `resources/` on disk today only holds `resources/clues/top_level_param_clues.yaml`.

## Key Conventions

- **Module naming**: CLI uses kebab-case (e.g. `bamber19-icesheets`); config filenames use snake_case (e.g. `bamber19_icesheets_module.yaml`). Conversion with `.replace("-", "_")` is pervasive.
- **Input path routing**: `is_shared_input()` matches field names containing `location`, `fingerprint`, or `fp` and routes them to `shared-input-data`; all other inputs route to `module-specific-input-data/<module_name>/`.
- **Clue/value bundles**: `create_metadata_bundle(clue, value)` produces `{clue: ..., value: ...}` dicts. `is_metadata_value()` detects them. Both live in `core/components/metadata_bundle.py`. In the Jinja2 template they render as commented hints for fields the user must fill in.
- **Per-workflow services**: facts-total and ESL modules produce one Compose service per workflow (e.g. `facts-total-wf1-global`, `facts-total-wf1-local`), not a single shared service.
