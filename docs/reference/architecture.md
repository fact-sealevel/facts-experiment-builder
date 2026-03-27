# Architecture

!!! note "This page is for codebase contributors"
    This is for developers modifying the experiment builder itself. If you want to add a new module, see [Adding a Module](../contributing/adding-a-module.md). If you just want to run experiments, see the [User Guide](../user-guide/overview.md).

`facts-experiment-builder` follows a layered architecture:

```
CLI → Application → Adapters → Core (domain) → Infrastructure → Resources
```

## Layers

### CLI (`src/facts_experiment_builder/cli/`)

Click commands. `setup-new-experiment` and `generate-compose` are the two main entry points. Both assume they are run from a project root that has an `experiments/` subdirectory. The setup CLI handles interactive workflow definition when `facts-total` is included, and accepts step-level data bypass options (`--climate-step-data`, `--supplied-totaled-sealevel-data`).

### Application (`application/`)

Orchestrates use cases.

| Module | Role |
|--------|------|
| `setup_new_experiment.py` | Builds a `FactsExperiment` from an `ExperimentSkeleton` + module YAMLs, populates defaults, writes `experiment-metadata.yml` via Jinja2. `hydrate_experiment()` constructs the four step objects; `hydrate_sealevel_step()` merges climate data paths into sealevel modules that need it. |
| `generate_compose.py` | Loads a completed `experiment-metadata.yml`, builds `FactsExperiment`, creates a `ModuleServiceSpec` per active module, produces `experiment-compose.yaml`. Steps configured with pre-existing data produce no Docker services. Per-workflow services are generated for `facts-total` and ESL modules. |

### Adapters (`adapters/`)

Translate between domain objects and I/O formats.

| Module | Role |
|--------|------|
| `experiment_metadata_to_service_spec.py` | Main translation function `build_module_service_spec()` — loads module YAML, resolves experiment paths, resolves typed inputs/outputs, builds `ModuleServiceSpecComponents` and `ModuleServiceSpec`. Handles special cases: ipccar5 shared dir, ESL per-workflow services, output-relative inputs. |
| `compose_service_writer.py` | Converts `ModuleServiceSpec` → Docker Compose service dict (image, command, volumes, depends_on). Strips `"main"` from `command[0]` if present. |
| `module_adapter.py` | Thin bridge — loads metadata if not pre-loaded, delegates to `build_module_service_spec`. |
| `adapter_utils.py` | `is_metadata_value()` detects clue/value dicts; `get_experiment_paths()` extracts path fields; `get_required_field()` / `get_required_field_with_alternatives()` for field extraction with error context. |

### Core (`core/`)

#### Experiment

| Class / Module | Role |
|----------------|------|
| `FactsExperiment` | In-memory representation of `experiment-metadata.yml`. Two constructors: `from_metadata_dict()` (parse loaded YAML) and `create_new_experiment_obj()` (build from CLI inputs). Holds the four step objects. |
| `ExperimentSkeleton` | Captures CLI intent before any YAML loading. Holds step module names and data-bypass paths. Passed to `hydrate_experiment()` to produce the full `FactsExperiment`. |

#### Steps

| Class | Role |
|-------|------|
| `ClimateStep` | Holds either a `ModuleExperimentSpec` (module runs) or `alternate_climate_data` path (module skipped). `not_needed()` class method marks the step as satisfied when totaled sealevel data is supplied. |
| `SealevelStep` | Holds a list of `ModuleExperimentSpec` objects, or a `supplied_totaled_sealevel_data` path. `is_configured()` returns `True` if either modules are fully configured or totaled data is present. |
| `TotalingStep` | Holds an optional `ModuleExperimentSpec`. `None` when the totaling step is skipped. |
| `ExtremeSealevelStep` | Holds an optional `ModuleExperimentSpec`. |
| `steps_from_metadata()` | Factory function (`core/steps/factories.py`) that rebuilds all four step objects from a loaded metadata dict. |

#### Modules

| Class / Module | Role |
|----------------|------|
| `ModuleExperimentSpec` | In-memory representation of one module's section in `experiment-metadata.yml`. `from_module_schema()` builds an initial spec with clue/value placeholders; `from_dict()` parses a loaded metadata dict. `is_configured()` returns `True` if no unfilled clue/value bundles remain. `to_dict()` serializes back to YAML shape. |
| `ModuleSchema` | Dataclass for a module YAML. Fields: `module_name`, `container_image`, `arguments`, `volumes`, `depends_on`, `command`, `uses_climate_file`, `extra`. |
| `ModuleServiceSpec` | Fully resolved spec for one Docker Compose service. `generate_compose_service()` orchestrates `_build_command_args()`, `_build_volumes()`, `_build_depends_on()`. Arguments processed in YAML order: `top_level → fingerprint_params → options → inputs → outputs`. Automatically adds depends_on for the climate service when `uses_climate_file` is true. |

#### Other core

| Class / Module | Role |
|----------------|------|
| `Workflow` | Frozen dataclass (`name` + `module_names`). Provides service naming and output filename conventions. `workflows_from_metadata()` / `workflows_to_metadata()` handle serialization. |
| `transforms.py` | `scenario_name_ssp_landwaterstorage()` maps scenario names for the `ssp-landwaterstorage` module using a bundled config YAML. |
| `source_resolver.py` | Resolves dot-separated source strings (e.g. `metadata.pipeline-id`, `module_inputs.outputs.foo`) against a context dict/object, with snake/kebab-case fallback. |
| `typed_path.py` | `TypedPath` with `HostPath`/`ContainerPath` constructors — used so the compose builder knows whether to rewrite a path to a container path or use it as-is. |
| `components/metadata_bundle.py` | `create_metadata_bundle(clue, value)` and `is_metadata_value()` — produce and detect `{clue: ..., value: ...}` dicts used as fill-in-the-blank hints in the Jinja2 template. |

### Infrastructure (`infra/`)

| Module | Role |
|--------|------|
| `path_manager.py` | Finds module YAML paths (`{module_name_snake}_module.yaml` in `resources/configs/`), experiment metadata files, and compose output paths. |
| `path_utils.py` | Expands `~` and env vars (`expand_path`), routes inputs to general vs module-specific base paths (`resolve_input_path`, `is_general_input`), resolves output paths (`resolve_output_path`). `resolve_experiment_directory_path()` uses `Path.cwd()` as project root. |
| `module_loader.py` / `module_defaults_loader.py` | Load `ModuleSchema` and defaults YAMLs from `resources/configs/`. |
| `experiment_loader.py` / `experiment_manager.py` | Load metadata YAML; create experiment directory structure including `data/output/` and per-module subdirs. |
| `write_experiment_metadata.py` | Jinja2 template for `experiment-metadata.yml`. Clue/value dicts render as YAML comments with optional placeholder values, guiding the user to fill in required fields. |
| `write_compose.py` | Serializes compose dict with `yaml.dump()`, then post-processes the string (`format_compose_yaml`) to enforce exact indentation and add double-quotes around command args. |

### Resources (`resources/configs/`)

Bundled `*_module.yaml` and `defaults_*.yml` files for all supported FACTS modules. `resources/__init__.py` exposes `get_module_configs_dir()` as the single source of truth for this directory.

---

## Key conventions

- **Module naming**: CLI uses kebab-case (e.g. `bamber19-icesheets`); config filenames use snake_case (e.g. `bamber19_icesheets_module.yaml`). Conversion with `.replace("-", "_")` is pervasive.
- **Input path routing**: `is_general_input()` matches field names containing `location`, `fingerprint`, or `fp` and routes them to `general-input-data`; all other inputs route to `module-specific-input-data/<module_name>/`.
- **Clue/value bundles**: `create_metadata_bundle(clue, value)` produces `{clue: ..., value: ...}` dicts. `is_metadata_value()` detects them. Both live in `core/components/metadata_bundle.py`. In the Jinja2 template they render as commented hints for fields the user must fill in.
- **Per-workflow services**: `facts-total` and ESL modules produce one Compose service per workflow (e.g. `facts-total-wf1-global`, `facts-total-wf1-local`), not a single shared service.
- **Step bypass**: Steps configured with pre-existing data (`alternate_climate_data`, `supplied_totaled_sealevel_data`) produce no Docker services. The `is_present` property on step objects controls whether a service is generated.
