# FACTS Glossary

Helpful guide to terms and how they are used in the FACTS v2 ecosystem.

---

## System / Ecosystem Level

### FACTS v2
Framework for Assessing Changes To Sea-level, version 2. A modular, containerized system for producing probabilistic projections of future sea-level rise. Each component of the computation (temperature, ice sheets, glaciers, extreme sea-level etc.) is encapsulated in an independent Docker container called a **module**.

### Module ecosystem
The full set of FACTS v2 modules — temperature, sea-level contribution, framework, and extreme sea-level — that can be composed together to produce a sea-level rise experiment.

### Module registry
A versioned collection of module YAML files (`*_module.yaml`) that describe all available FACTS v2 modules. Each entry defines the module's container image, input/output arguments, volumes, and command structure. The registry is the authoritative source for what modules exist and how to run them.

### Container image
A Docker image URL and tag (e.g., `ghcr.io/fact-sealevel/fair-temperature:0.2.1`) that identifies the exact, pinned version of a module to run. Specified in the module YAML and copied into the generated compose file.

### Pipeline ID
A unique string identifier for an experiment run (e.g., `my-experiment-ssp585`). Propagated to every module as `--pipeline-id` and used to name output files, so outputs from different modules within the same experiment can be matched up.

---

## Experiment Level

### Experiment
A named, fully-specified sea-level rise computation. An experiment selects a set of modules (one temperature module, one or more sea-level modules, a framework/totaling module, and optionally an extreme sea-level module), sets shared parameters, and defines one or more workflows. Everything needed to reproduce an experiment is captured in its `experiment-config.yaml`.

### experiment-config.yaml
The primary configuration file for a FACTS experiment. Written by the `setup-experiment` CLI command and edited by the user. Contains:
- **top-level parameters** shared across all modules (scenario, nsamps, pyear ranges, etc.)
- **module manifest** declaring which modules are included
- **module-specific sections** with inputs, options, outputs, and fingerprint parameters for each module
- **paths** to input data and output directories
- **workflows** defining how sea-level modules are combined for totaling

This file is the human-editable artifact; once complete it drives `generate-compose`.

### experiment-compose.yaml
A Docker Compose file generated from a completed `experiment-config.yaml` by the `generate-compose` CLI command. Contains one service definition per module (or per workflow for facts-total and ESL), with resolved image references, command arguments, volume mounts, and service dependencies. This file is used directly to run the experiment (e.g., `docker compose -f experiment-compose.yaml up`).

### Top-level parameters
Parameters defined once at the experiment level and automatically passed to every module that declares them. Common top-level parameters include:

| Parameter | Description |
|---|---|
| `scenario` | Emissions scenario identifier (e.g., `ssp585`, `ssp245`, `rcp85`) |
| `nsamps` | Number of Monte Carlo samples to generate |
| `seed` | Random seed for reproducibility |
| `pyear-start` | First projection year (e.g., `2020`) |
| `pyear-end` | Last projection year (e.g., `2100`) |
| `pyear-step` | Interval between projection years (e.g., `10`) |
| `baseyear` | Reference year for relative sea-level calculations (e.g., `2005`) |
| `location-file` | Path to a CSV of named locations (id, name, lat, lon) for localized projections |

### Scenario
An emissions pathway identifier used to select the appropriate climate forcing data. Common values: `ssp585`, `ssp245`, `ssp126`, `rcp85`. Some modules (e.g., `ssp-landwaterstorage`) require scenario names in a different format — the experiment builder handles this translation automatically via a scenario name transform.

### Manifest
The section of `experiment-config.yaml` that declares which module fills each role in the experiment:

```yaml
manifest:
  temperature_module: fair-temperature
  sealevel_modules:
    - bamber19-icesheets
    - ipccar5-glaciers
  framework_module: facts-total
  extreme_sealevel_module: extremesealevel-pointsoverthreshold
```

### Paths
The section of `experiment-config.yaml` that declares the three root directories for the experiment:

| Field | Description |
|---|---|
| `shared-input-data` | Shared inputs used by multiple modules (location files, fingerprint data) |
| `module-specific-input-data` | Per-module input data directories |
| `output-data-location` | Root directory where all module outputs are written |

---

## Module Level

### Module
A self-contained computational step packaged as a Docker container. A module takes inputs (parameter values, data files) and produces outputs (NetCDF files) for a specific physical contribution to sea-level rise or for aggregation/analysis. Modules are independent — they communicate only through the file system.

### Module types
Modules are assigned one of four roles in an experiment:

| Type | Description | Example |
|---|---|---|
| `temperature_module` | Produces climate forcing data (temperature trajectories) consumed by sea-level modules | `fair-temperature`, `fair2-climate` |
| `sealevel_module` | Computes a single physical contribution to sea-level rise (e.g., glaciers, ice sheets, VLM) | `bamber19-icesheets`, `ipccar5-glaciers`, `tlm-sterodynamics` |
| `framework_module` | Sums sea-level contributions across modules for each workflow | `facts-total` |
| `extreme_sealevel_module` | Computes extreme sea-level statistics from total sea-level projections | `extremesealevel-pointsoverthreshold` |

### Module YAML (`*_module.yaml`)
The file in the module registry that fully describes a module. Key sections:

- **`container_image`** — Docker image URL:tag for the module
- **`arguments`** — Declares all command-line arguments the container accepts, organized by subsection (see below)
- **`volumes`** — Volume mount definitions (host directory → container path)
- **`command`** — Optional sub-command (for modules with multiple entry points, e.g., `glaciers` vs. `icesheets`)
- **`uses_climate_file`** — Boolean; if true, this module depends on the temperature module's output and `depends_on` the temperature service in compose
- **`extra`** — Module-specific miscellaneous configuration (e.g., `per_workflow`, `skip_fingerprint_params`)

### Argument sections
Within a module YAML, arguments are divided into subsections that control where their values come from and how they appear in the compose command:

| Section | Source |
|---|---|
| `top_level` | Resolved from top-level experiment parameters (e.g., `metadata.nsamps`) |
| `fingerprint_params` | Resolved from fingerprint parameter fields in the experiment config |
| `options` | Module-specific scalar options defined in the module's experiment config section |
| `inputs` | Input file paths defined in the module's experiment config section |
| `outputs` | Output file paths; filenames are defined in the module YAML and resolved at compose generation time |

### Source
A dot-separated string in a module YAML that tells the experiment builder where to look up an argument's value. Examples:
- `metadata.pipeline-id` → the experiment's top-level `pipeline-id`
- `metadata.nsamps` → the experiment's top-level `nsamps`
- `module_inputs.options.seed` → the `seed` field in this module's options section
- `module_inputs.inputs.rcmip_fname` → the `rcmip_fname` field in this module's inputs section

### Clue / value bundle
A `{clue: "...", value: ...}` dictionary used as a placeholder in `experiment-config.yaml` for fields that the user must fill in. The `clue` is a human-readable hint explaining what value is expected; `value` holds the actual data once the user populates it. The experiment builder uses clue/value bundles to produce self-documenting config templates.

### Fingerprint parameters
Parameters used in probabilistic ensemble generation — typically `fingerprint-dir` (a directory of fingerprint data for spatial disaggregation) and `location-file`. Declared separately from regular options because they route to the shared input directory rather than the module-specific input directory.

### `uses_climate_file`
A boolean field in a module YAML. When `true`, the module reads the temperature output file produced by the temperature module and the generated compose service will have a `depends_on` dependency on the temperature service.

---

## Workflow Level

### Workflow
A named grouping of sea-level modules whose contributions will be summed by the framework module (`facts-total`) to produce a total sea-level projection. An experiment can define multiple workflows to compare different combinations of modules. Example:

```yaml
workflows:
  wf1:
    - bamber19-icesheets
    - ipccar5-glaciers
    - tlm-sterodynamics
    - ssp-landwaterstorage
  wf2:
    - deconto21-ais
    - ipccar5-glaciers
    - tlm-sterodynamics
    - ssp-landwaterstorage
```

### facts-total
The framework module that sums sea-level contributions from all modules in a workflow. It produces both global and local total sea-level projections. Unlike other modules, facts-total generates one compose service per workflow per output type (e.g., `facts-total-wf1-global`, `facts-total-wf1-local`), not a single service.

### Per-workflow services
When facts-total and extreme sea-level modules are included, the compose file contains one service instance per workflow (and per output type for facts-total). Service names follow the pattern `facts-total-<workflow_name>-<output_type>` (e.g., `facts-total-wf1-global`, `facts-total-wf2-local`).

### Output types
Facts-total and ESL modules produce outputs classified by spatial scope:

| Type | Description |
|---|---|
| `global` | Spatially-averaged or global-mean output |
| `local` | Location-specific output for each site in the location file |

---

## Step Level

Steps represent the four ordered phases of a FACTS experiment. Each step maps to one or more module types and must complete before the next step begins.

### Climate step
The first step. Runs the `temperature_module` to produce climate forcing data (temperature trajectories) from emissions scenarios. Output is consumed by all sea-level modules that declare `uses_climate_file: true`.

### Sea-level step
The second step. Runs all `sealevel_modules` in parallel (they are independent of each other, but all depend on the climate step if they use climate data). Each module computes its physical contribution to sea-level rise (e.g., glacier melt, ice sheet dynamics, sterodynamics, vertical land motion).

### Totaling step
The third step. Runs `facts-total` (the `framework_module`) once per workflow to sum the sea-level contributions from all modules in that workflow, producing total sea-level projections (global and/or local).

### Extreme sea-level step
The fourth step. Runs the `extreme_sealevel_module` on the totaled sea-level projections to compute return levels and other extreme sea-level statistics. Depends on the totaling step completing first.

---

## Compose / Service Level

These terms describe how modules are represented in the generated `experiment-compose.yaml`.

### Service
A single container execution unit in the compose file, corresponding to one module run. Each service specifies the container image, command arguments, volume mounts, and dependencies. Facts-total and ESL modules produce multiple services (one per workflow or workflow/type combination).

### Command arguments
All module arguments are passed as `--name=value` flags in the container command. Arguments are ordered in the compose command as: `top_level` → `fingerprint_params` → `options` → `inputs` → `outputs`. File paths are rewritten to their container-side mount paths.

### Volumes
Directory bindings that make host paths available inside a container. Each volume is expressed as `host_path:container_path`. Standard container mount points used across modules:

| Container path | Contents |
|---|---|
| `/mnt/module_specific_in` | Module-specific input data |
| `/mnt/shared_in` | Shared inputs (location files, fingerprint directories) |
| `/mnt/out` | All module outputs |
| `/mnt/experiment_specific_in` | User-supplied experiment data (e.g., custom climate files) |
| `/mnt/total_in` | Input to facts-total (sea-level contributions from other modules) |
| `/mnt/total_out` | Output from facts-total |

### `depends_on`
A compose field listing services that must complete successfully before this service starts. Generated automatically based on module type (sea-level modules depend on the temperature service if `uses_climate_file` is true; totaling depends on all sea-level modules; ESL depends on totaling).

### Shared input data
Input files used by multiple modules, routed to `/mnt/shared_in` in the container. Fields are classified as shared inputs if their name contains `location`, `fingerprint`, or `fp`. All other input fields are treated as module-specific inputs routed to `/mnt/module_specific_in`.

### Module-specific input data
Input data files that belong to a single module. Stored under `module-specific-input-data/<module_name>/` on the host and mounted at `/mnt/module_specific_in` in the container.