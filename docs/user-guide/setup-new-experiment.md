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
| `--climate-step TEXT` | No | Climate module name (e.g. `fair-temperature`) |
| `--supplied-climate-step-data PATH` | No | Path to pre-existing climate data — runs no climate module |
| `--sealevel-step TEXT` | No | Comma-separated list of sea-level module names |
| `--supplied-totaled-sealevel-step-data PATH` | No | Path to pre-existing totaled sealevel data — skips climate, sealevel, and totaling steps |
| `--totaling-step TEXT` | No | Totaling module name, or `NONE` (default: `facts-total`) |
| `--extremesealevel-step TEXT` | No | Extreme sea-level module name, or `NONE` |
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

Running `setup-new-experiment` performs these steps:

1. Creates `experiments/<experiment-name>/` in your project root
2. Creates standard subdirectories (`data/output/`, per-module subdirs) and placeholder files
3. Builds a `FactsExperiment` from your CLI arguments and the bundled module YAML configs
4. Merges default values from each module's `defaults_*.yml`
5. Writes `experiment-metadata.yml` using a Jinja2 template — fields you did not supply are left as commented hints for you to fill in

If `facts-total` is specified as the `--totaling-step`, the CLI interactively prompts you to name and configure the experiment's workflows before writing the metadata file.

## Examples

### Full run — all steps run modules

```shell
setup-new-experiment \
  --experiment-name toy_experiment \
  --pipeline-id aaa \
  --scenario ssp585 \
  --pyear-start 2020 --pyear-end 2100 --pyear-step 10 \
  --baseyear 2005 --seed 1234 --nsamps 1000 \
  --climate-step fair-temperature \
  --sealevel-step bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,nzinsargps-verticallandmotion,kopp14-verticallandmotion \
  --totaling-step facts-total \
  --extremesealevel-step extremesealevel-pointsoverthreshold
```

### Supply pre-existing climate data (skip climate step)

Use `--supplied-climate-step-data` to provide the path to an existing climate output file (e.g. a FAIR run you already have). The sealevel modules that require climate input will automatically receive this path, and no climate service will be added to the compose file.

```shell
setup-new-experiment \
  --experiment-name my_exp_with_climate_data \
  --scenario ssp585 \
  --pyear-start 2020 --pyear-end 2100 --pyear-step 10 \
  --baseyear 2005 --seed 1234 --nsamps 1000 \
  --supplied-climate-step-data /path/to/climate_data.nc \
  --sealevel-step bamber19-icesheets,tlm-sterodynamics \
  --totaling-step facts-total \
  --extremesealevel-step extremesealevel-pointsoverthreshold
```

### Supply pre-existing totaled sealevel data (skip climate, sealevel, and totaling steps)

Use `--supplied-totaled-sealevel-step-data` to provide the path to already-computed totaled sea level output. This skips the climate and sealevel steps entirely. The totaling step is also automatically omitted (since there is nothing to total).

```shell
setup-new-experiment \
  --experiment-name my_exp_esl_only \
  --scenario ssp585 \
  --pyear-start 2020 --pyear-end 2100 --pyear-step 10 \
  --baseyear 2005 --seed 1234 --nsamps 1000 \
  --supplied-totaled-sealevel-step-data /path/to/totaled_sealevel.nc \
  --extremesealevel-step extremesealevel-pointsoverthreshold
```

!!! note
    After this command completes, open `experiments/<experiment-name>/experiment-metadata.yml` and fill in any remaining empty fields (especially `module-specific-inputs` and `general-inputs` if you did not pass them as CLI arguments).

## After setup

Once the metadata file is complete, run [`generate-compose`](generate-compose.md) to produce the Docker Compose file.
