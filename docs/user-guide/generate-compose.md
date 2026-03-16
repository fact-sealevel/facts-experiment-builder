# generate-compose

Reads a completed `experiment-metadata.yml` and generates a Docker Compose file for the experiment.

## Usage

```shell
generate-compose [OPTIONS]
```

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--experiment-name TEXT` | Yes | Name of the experiment (looks in `experiments/` directory) |
| `--custom-output-path PATH` | No | Custom output path for the compose file. If provided, must include the full path and use filename `experiment-compose.yaml`. Defaults to `experiments/<name>/experiment-compose.yaml`. |
| `-h, --help` | — | Show help and exit |

## What it does

1. Locates `experiments/<experiment-name>/experiment-metadata.yml` from your project root
2. Loads the metadata and builds a `FactsExperiment` in memory
3. For each module in the manifest (temperature, sealevel, framework, ESL), builds a fully resolved `ModuleServiceSpec` — resolving input/output paths, command arguments, volumes, and service dependencies
4. For `facts-total` and ESL modules, generates one service per workflow (e.g. `facts-total-wf1-global`, `facts-total-wf1-local`)
5. Serializes all services to `experiment-compose.yaml`

!!! warning
    If the temperature module is `NONE`, `generate-compose` validates that the required climate file inputs are present for each sea-level module before writing the compose file.

## Example

```shell
generate-compose --experiment-name toy_experiment
```

Output: `experiments/toy_experiment/experiment-compose.yaml`

## Running the compose file

```shell
docker compose -f experiments/toy_experiment/experiment-compose.yaml up
```
