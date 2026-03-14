# Overview

## What this tool does

`facts-experiment-builder` has two jobs:

1. **`setup-new-experiment`** — scaffolds a new experiment directory and generates a pre-populated `experiment-metadata.yml` from your CLI arguments and bundled module YAML configs.
2. **`generate-compose`** — reads a completed `experiment-metadata.yml` and produces a Docker Compose file (`experiment-compose.yaml`) that runs the experiment.

The `experiment-metadata.yml` is the central artifact: it is an abstract, run-environment-agnostic specification of the full experiment. Docker is the first supported execution backend; an Async-Flow backend is planned but not yet implemented.

---

## Key concepts

### Experiment

An experiment is a named collection of modules, top-level parameters, and workflows. It lives under `experiments/<experiment-name>/` in your project root.

**Top-level parameters** apply across all modules:

| Parameter | Description |
|-----------|-------------|
| `pipeline-id` | Unique identifier for this pipeline run |
| `scenario` | Climate scenario (e.g. `ssp585`) |
| `nsamps` | Number of samples |
| `seed` | Random seed |
| `baseyear` | Base year for projections |
| `pyear-start` / `pyear-end` / `pyear-step` | Projection year range |

### Module

A module is a containerized application that computes one component of sea-level rise (e.g. ice sheet contribution, sterodynamics, vertical land motion). Each module has:

- A **module YAML** (e.g. `bamber19_icesheets_module.yaml`) describing its inputs, outputs, arguments, and container image.
- An optional **defaults YAML** (e.g. `defaults_bamber19_icesheets.yml`) with default parameter values.

Modules are organized into four categories:

| Category | CLI flag | Description |
|----------|----------|-------------|
| Temperature | `--temperature-module` | Provides climate forcing (or `NONE` to supply pre-computed climate files) |
| Sea level | `--sealevel-modules` | One or more sea-level contribution modules (comma-separated) |
| Framework | `--framework-module` | Aggregation module (currently `facts-total`) |
| Extreme sea level | `--extremesealevel-module` | ESL module (e.g. `extremesealevel-pointsoverthreshold`) |

See [Available Modules](modules.md) for the full list.

### Workflow

A workflow is a named combination of sea-level modules whose outputs are summed to produce a total sea-level projection. Experiments can contain multiple workflows (e.g. one using `bamber19-icesheets` and another using `larmip-ais` for the Antarctic contribution).

When `facts-total` is the framework module, the CLI prompts you to define workflows interactively during `setup-new-experiment`.

### experiment-metadata.yml

This is the source of truth for the experiment. It contains:
- Top-level parameters
- The module manifest (which modules are included)
- Input/output path configuration
- Per-module argument sections (pre-populated from module YAMLs and defaults)
- Workflow definitions

You review and complete this file after `setup-new-experiment` before running `generate-compose`.
