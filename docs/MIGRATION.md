# Migrating to the new `experiment-config.yaml` format

**Applies to:** FEB versions after 0.5.0 ([PR #115](https://github.com/fact-sealevel/facts-experiment-builder/pull/115))

## What changed

`feb setup-experiment` now saves a copy of each module's schema (container image, arguments, volumes) from the module registry into a new `module_schemas` section at the end of `experiment-config.yaml`. `feb generate-compose` reads module information from that section and **no longer uses the module registry**.

Why:
- **`experiment-config.yaml` files are now fully self-describing.** An experiment's compose file is built from the module versions it was set up with, even if the registry has changed since.
- **`generate-compose` doesn't need the registry.** You can generate a compose file on a machine without a checkout of `facts-module-registry`.

The new section looks like this (see [EXPERIMENT-CONFIG-OVERVIEW.md](EXPERIMENT-CONFIG-OVERVIEW.md) for the full file layout):

```yaml
##----- Module schemas -----##
# Auto-generated. Do not edit.
module_registry_version: local@9b5e30c   # version of the module registry used to generate this file

module_schemas:
  fair-temperature:
    module_name: fair-temperature
    container_image: "ghcr.io/fact-sealevel/fair-temperature:0.2.1"
    arguments: { ... }
    volumes: { ... }
```

The rest of `experiment-config.yaml` (top-level parameters, paths, workflows and the module sections you fill in) is unchanged.

## Do I need to migrate?

Yes, if you made an experiment with FEB 0.5.0 or earlier and want to run `feb generate-compose` on it with a newer FEB. It will stop with:

```
ValueError: This experiment's experiment-config.yaml file does not contain a 'module_schemas' section. ...
Please ensure you are using the latest version of FEB and re-run `setup-experiment`.
```

If you already ran `generate-compose` on an old experiment and don't need to regenerate its compose file, you can leave it as it is. The existing `experiment-compose.yaml` still works.

## How to migrate an experiment

You can't add the new section to an old file in place. Regenerate the config with `setup-experiment`, then copy over any values you edited by hand.

### 1. Move the old experiment directory aside

`setup-experiment` won't overwrite an existing experiment (it raises `ExperimentAlreadyExistsError`), so rename the old directory first:

```bash
mv experiments/my-experiment experiments/my-experiment-old
```

### 2. Re-run `setup-experiment` with the same options

Use the same modules, top-level parameters and paths as the original run. If you don't have the original command any more, you can rebuild it from the old config: the manifest (module names), top-level parameters (`pipeline-id`, `scenario`, `baseyear`, `pyear-*`, `nsamps`, `location-file`), paths and projection scale are all at the top of the old `experiment-config.yaml`.

```bash
feb setup-experiment \
  --experiment-name experiments/my-experiment \
  --climate-step fair-temperature \
  --sealevel-step tlm-sterodynamics \
  --pipeline-id my-run --scenario ssp126 --baseyear 2005 \
  --pyear-start 2020 --pyear-end 2100 --pyear-step 10 \
  --nsamps 500 --location-file location.lst \
  --module-specific-input-data ./data/module_specific_input_data \
  --shared-input-data ./data/shared_input_data \
  --projection-scale local
```

`setup-experiment` still reads from the module registry (`--module-registry`, default `facts-module-registry`). The module versions saved in the new config are the ones in your registry checkout **now**. If you need exactly the versions the old experiment used, check out the matching registry commit before running this step.

If the experiment used custom workflows, answer the workflow prompts the same way you did before. They're listed under `workflows` in the old config.

### 3. Copy over values you edited by hand

Compare the old and new config files:

```bash
diff experiments/my-experiment-old/experiment-config.yaml \
     experiments/my-experiment/experiment-config.yaml
```

Copy any values you changed in the old file's module sections (inputs, options, outputs) into the new file. Apart from those edits, the only difference you should see is the new `module_schemas` section.

**Don't edit `module_schemas` or `module_registry_version`.** They're generated automatically.

### 4. Generate the compose file

```bash
feb generate-compose --experiment-name experiments/my-experiment
```

### 5. Clean up

Once the new experiment works, delete `my-experiment-old`. If it has output data you want to keep, move that into the new experiment directory first.

## Other changes to `generate-compose`

- **`--module-registry` has been removed from `generate-compose`.** Scripts that pass it will fail with `No such option: --module-registry`. Remove the flag. `setup-experiment` still accepts it.
- **Registry updates no longer reach existing experiments.** Before, running `generate-compose` again picked up whatever was in your registry checkout. Now it always uses the schemas saved at setup time. To move an experiment to newer module versions, repeat the steps above.

## Troubleshooting

- **"`experiment-config.yaml` is missing module schema information for: `<module>`"**: the `module_schemas` section exists but doesn't include every module the experiment uses. This usually means the file was edited by hand to add a module. Re-run `setup-experiment` with the full set of modules.
- **"Experiment already exists at path …"**: you skipped step 1. Rename or remove the existing experiment directory, or use a different `--experiment-name`.
- If you are still having trouble, please raise an issue [here](https://github.com/fact-sealevel/facts-experiment-builder/issues) or post on the FACTS Slack workspace! 