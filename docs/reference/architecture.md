# Architecture

!!! note "This page is for codebase contributors"
    This is for developers modifying the experiment builder itself. If you want to add a new module, see [Adding a Module](../contributing/adding-a-module.md). If you just want to run experiments, see the [User Guide](../user-guide/overview.md).

`facts-experiment-builder` follows a layered architecture:

```
CLI → Application → Adapters → Core (domain) → Infrastructure → Resources
```

## Layers

### CLI (`src/facts_experiment_builder/cli/`)

Click commands. `setup-new-experiment` and `generate-compose` are the two main entry points. Both assume they are run from a project root that has an `experiments/` subdirectory. The setup CLI handles interactive workflow definition when `facts-total` is included.

### Application (`application/`)

Orchestrates use cases.

| Module | Role |
|--------|------|
| `setup_new_experiment.py` | 5-step flow: creates `experiments/<name>/`, builds a `FactsExperiment` from CLI args + module YAMLs, populates defaults, writes `experiment-metadata.yml` via Jinja2 |
| `generate_compose.py` | Loads a completed `experiment-metadata.yml`, builds `FactsExperiment`, creates a `ModuleServiceSpec` per module, produces `experiment-compose.yaml`. Validates climate file inputs when temperature module is `NONE`. Per-workflow services are generated for `facts-total` and ESL modules. |

### Adapters (`adapters/`)

Translate between domain objects and I/O formats.

| Module | Role |
|--------|------|
| `experiment_metadata_to_service_spec.py` | Main translation function `build_module_service_spec()` — loads module YAML, resolves experiment paths, resolves typed inputs/outputs, builds `ModuleServiceSpecComponents` and `ModuleServiceSpec`. Handles special cases: ipccar5 shared dir, ESL per-workflow services, output-relative inputs. |
| `compose_service_writer.py` | Converts `ModuleServiceSpec` → Docker Compose service dict (image, command, volumes, depends_on). Strips `"main"` from `command[0]` if present. |
| `module_adapter.py` | Thin bridge — loads metadata if not pre-loaded, delegates to `build_module_service_spec`. |
| `adapter_utils.py` | `is_metadata_value()` detects clue/value dicts; `get_experiment_paths()` extracts path fields; `get_required_field()` / `get_required_field_with_alternatives()` for field extraction with error context. |

### Core (`core/`)

| Class / Module | Role |
|----------------|------|
| `FactsExperiment` | In-memory representation of `experiment-metadata.yml`. Two constructors: `from_metadata_dict()` (parse loaded YAML) and `create_new_experiment_obj()` (build from CLI inputs). `merge_defaults_for_module()` merges a defaults YAML into the module section with snake/kebab-case flexibility. |
| `FactsModule` | Dataclass for a module YAML. Fields: `module_name`, `container_image`, `arguments` (with keys `top_level`, `options`, `inputs`, `outputs`, `fingerprint_params`), `volumes`, `depends_on`, `command`, `uses_climate_file`, `extra`. |
| `ModuleServiceSpec` | Fully resolved spec for one Docker Compose service. `generate_compose_service()` orchestrates `_build_command_args()`, `_build_volumes()`, `_build_depends_on()`. Arguments are processed in YAML order: `top_level → fingerprint_params → options → inputs → outputs`. Automatically adds depends_on for temperature service when `uses_climate_file` is true. |
| `Workflow` | Frozen dataclass (`name` + `module_names`). Provides service naming and output filename conventions. `workflows_from_metadata()` / `workflows_to_metadata()` handle serialization. |
| `transforms.py` | `scenario_name_ssp_landwaterstorage()` maps scenario names for the `ssp-landwaterstorage` module using a bundled config YAML. |
| `source_resolver.py` | Resolves dot-separated source strings (e.g. `metadata.pipeline-id`, `module_inputs.outputs.foo`) against a context dict/object, with snake/kebab-case fallback. |
| `typed_path.py` | `TypedPath` with `HostPath`/`ContainerPath` constructors — used so the compose builder knows whether to rewrite a path to a container path or use it as-is. |

### Infrastructure (`infra/`)

| Module | Role |
|--------|------|
| `path_manager.py` | Finds module YAML paths (`{module_name_snake}_module.yaml` in `resources/configs/`), experiment metadata files, and compose output paths. |
| `path_utils.py` | Expands `~` and env vars (`expand_path`), routes inputs to general vs module-specific base paths (`resolve_input_path`, `is_general_input`), resolves output paths (`resolve_output_path`). `find_project_root()` walks up from cwd looking for `pyproject.toml`. |
| `module_loader.py` / `module_defaults_loader.py` | Load `FactsModule` and defaults YAMLs from `resources/configs/`. |
| `experiment_loader.py` / `experiment_manager.py` | Load metadata YAML; create experiment directory structure including `data/output/` and per-module subdirs. |
| `write_experiment_metadata.py` | Jinja2 template for `experiment-metadata.yml`. Clue/value dicts render as YAML comments with optional placeholder values, guiding the user to fill in required fields. |
| `write_compose.py` | Serializes compose dict with `yaml.dump()`, then post-processes the string (`format_compose_yaml`) to enforce exact indentation and add double-quotes around command args. |

### Resources (`resources/configs/`)

Bundled `*_module.yaml` and `defaults_*.yml` files for all supported FACTS modules. `resources/__init__.py` exposes `get_module_configs_dir()` as the single source of truth for this directory.

---

## Key conventions

- **Module naming**: CLI uses kebab-case (e.g. `bamber19-icesheets`); config filenames use snake_case (e.g. `bamber19_icesheets_module.yaml`). Conversion with `.replace("-", "_")` is pervasive.
- **Input path routing**: `is_general_input()` matches field names containing `location`, `fingerprint`, or `fp` and routes them to `general-input-data`; all other inputs route to `module-specific-input-data/<module_name>/`.
- **Clue/value bundles**: `create_metadata_bundle(clue, value)` produces `{clue: ..., value: ...}` dicts. `is_metadata_value()` detects them. In the Jinja2 template they render as commented hints for fields the user must fill in.
- **Per-workflow services**: `facts-total` and ESL modules produce one Compose service per workflow (e.g. `facts-total-wf1-global`, `facts-total-wf1-local`), not a single shared service.
- **`find_project_root()`** is in `infra/path_utils.py`, not `path_manager.py`.
