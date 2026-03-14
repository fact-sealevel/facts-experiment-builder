# setup-new-experiment

Initializes a new experiment directory and generates a pre-populated `experiment-metadata.yml`.

## Usage

```shell
setup-new-experiment [OPTIONS]
```

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--experiment-name TEXT` | Yes | Name of the experiment |
| `--temperature-module TEXT` | Yes | Temperature module name, or `NONE` |
| `--sealevel-modules TEXT` | Yes | Comma-separated list of sea-level module names |
| `--framework-module TEXT` | No | Framework module name, or `NONE` |
| `--extremesealevel-module TEXT` | No | Extreme sea-level module name, or `NONE` |
| `--pipeline-id TEXT` | No | Pipeline ID |
| `--scenario TEXT` | No | Climate scenario (e.g. `ssp585`) |
| `--baseyear INTEGER` | No | Base year |
| `--pyear-start INTEGER` | No | Projection year start |
| `--pyear-end INTEGER` | No | Projection year end |
| `--pyear-step INTEGER` | No | Projection year step |
| `--nsamps INTEGER` | No | Number of samples |
| `--seed INTEGER` | No | Random seed |
| `--location-file TEXT` | No | Location file name |
| `--fingerprint-dir TEXT` | No | Directory name for GRD fingerprint data |
| `--module-specific-inputs TEXT` | No | Path to module-specific input data |
| `--general-inputs TEXT` | No | Path to general input data |
| `-h, --help` | — | Show help and exit |

## What it does

Running `setup-new-experiment` performs five steps:

1. Creates `experiments/<experiment-name>/` in your project root
2. Creates standard subdirectories (`data/output/`, per-module subdirs) and placeholder files
3. Builds a `FactsExperiment` from your CLI arguments and the bundled module YAML configs
4. Merges default values from each module's `defaults_*.yml`
5. Writes `experiment-metadata.yml` using a Jinja2 template — fields you did not supply are left as commented hints for you to fill in

If `facts-total` is specified as the `--framework-module`, the CLI interactively prompts you to name and configure the experiment's workflows before writing the metadata file.

## Example

```shell
setup-new-experiment \
  --experiment-name toy_experiment \
  --pipeline-id aaa \
  --scenario ssp585 \
  --pyear-start 2020 --pyear-end 2100 --pyear-step 10 \
  --baseyear 2005 --seed 1234 --nsamps 1000 \
  --temperature-module fair-temperature \
  --sealevel-modules bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,nzinsargps-verticallandmotion,kopp14-verticallandmotion \
  --framework-module facts-total \
  --extremesealevel-module extremesealevel-pointsoverthreshold
```

!!! note
    After this command completes, open `experiments/<experiment-name>/experiment-metadata.yml` and fill in any remaining empty fields (especially `module-specific-inputs` and `general-inputs` if you did not pass them as CLI arguments).

## After setup

Once the metadata file is complete, run [`generate-compose`](generate-compose.md) to produce the Docker Compose file.
