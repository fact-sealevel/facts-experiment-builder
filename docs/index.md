# facts-experiment-builder

> [!CAUTION]
> This is a prototype. It is likely to change in breaking ways. It might delete all your data. Don't use it in production.

## Overview

`facts-experiment-builder` is a CLI tool for configuring and managing [FACTS v2](https://github.com/fact-sealevel/FACTS) sea-level rise experiments.

A FACTS v2 experiment consists of running one or more containerized modules from the FACTS v2 ecosystem. It typically has a set of **top-level parameters** shared across all modules (e.g. `nsamps`, `scenario`, `pyear-start/end/step`, `baseyear`) and one or more **workflows** — combinations of sea-level modules that are summed to produce output distributions of projected future sea-level rise.

This package centers around physical artifacts and core in-memory representations:

- An **experiment** is defined as a set of parameters, a collection of modules, and a list of workflows. It is serialized as `experiment-metadata.yml` and represented in-memory by the `FactsExperiment` class.
- Each containerized module has a corresponding **module YAML** (e.g. `bamber19_icesheets_module.yaml`) and an optional **defaults YAML** (e.g. `defaults_bamber19_icesheets.yml`). In-memory, this is a `FactsModule` object.

## Two-step workflow

```
setup-new-experiment  →  (edit experiment-metadata.yml)  →  generate-compose  →  docker compose up
```

1. **`setup-new-experiment`** — creates `experiments/<name>/` and writes a pre-populated `experiment-metadata.yml`
2. **`generate-compose`** — reads the completed metadata and produces `experiment-compose.yaml` ready for Docker

## Quick example

```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main setup-new-experiment \
  --experiment-name toy_experiment \
  --pipeline-id aaa --scenario ssp585 \
  --pyear-start 2020 --pyear-end 2100 --pyear-step 10 \
  --baseyear 2005 --seed 1234 --nsamps 1000 \
  --temperature-module fair-temperature \
  --sealevel-modules bamber19-icesheets,tlm-sterodynamics,ipccar5-glaciers \
  --framework-module facts-total \
  --extremesealevel-module extremesealevel-pointsoverthreshold
```

See [Quickstart](getting-started/quickstart.md) for the full walkthrough.

## Documentation sections

| Section | Audience |
|---------|----------|
| [Getting Started](getting-started/installation.md) | Everyone — install and run your first experiment |
| [User Guide](user-guide/overview.md) | Experiment users — CLI reference, modules, concepts |
| [Contributing](contributing/overview.md) | Developers — codebase architecture, call graphs, how to add modules |

## Source & support

- Source: [github.com/fact-sealevel/facts-experiment-builder](https://github.com/fact-sealevel/facts-experiment-builder)
- Issues: [github.com/fact-sealevel/facts-experiment-builder/issues](https://github.com/fact-sealevel/facts-experiment-builder/issues)
- License: MIT
