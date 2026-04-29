[![codecov](https://codecov.io/gh/fact-sealevel/facts-experiment-builder/branch/main/graph/badge.svg)](https://codecov.io/gh/fact-sealevel/facts-experiment-builder)

# facts-experiment-builder

> [!CAUTION]
> This is a prototype. It is likely to change in breaking ways, please don't rely on it in production and check back regularly for updates and new releases.

## Overview
This is a prototype of a package for configuring and managing FACTS 2 experiments. A FACTS 2 experiment consists of running one or more modules from the FACTS 2 ecosystem. It usually has a set of specified 'top-level parameters' that apply across all of the modules in the experiment. These can include parameters such as `nsamps`, `pyear-start`, `pyear-step`, `pyear-end`, `baseyear`, and `scenario` and `location-file` if you would like to include localized projections in your experiment. Within an experiment, one can define multiple 'workflows`, these represent different combinations of sea-level modules to be summed to produce output distributions of projected future sea level rise. 

This package centers around physical artifacts, YAML files, and core in-memory representations of the artifacts. For example, an experiment is abstractly defined as a set of parameters, a collection of modules, and a list of workflows. This is store on disk as an `experiment-config.yaml` file and represented in-memory by the `FactsExperiment` class. 

Each containerized module application has a corresponding module yaml file (ie. `bamber19_icesheets_module.yaml` or `tlm_sterodynamics_module.yaml`). *Note: These yaml files are currently located in this repo, eventually they will be stored in the module repos.* The module yaml represents all of the inputs, outputs, and parameters used to specify that module as well as other critical metadata. In memory, this is stored as an object of the `ModuleSchema` class. Default values for parameters and filenames for input and output files are also stored in the module yaml files.

To run a FACTS 2 experiment, we need more than the abstract information stored in an `experiment-config.yaml`. `facts-experiment-builder` plans to offer implementations for multiple execution environments, with an experiment's `experiment-config.yaml` remainining the underlying source of 'truth' about the experiment. From here, run files can be generated for specific execution environments such as Docker (`experiment-compose.yml`) and Async-Flow (`async-flow-experiment.py`, **not yet implemented**).

## Getting started

Check out our [quickstart](QUICKSTART.md) guide for instructions on how to begin creating FACTS2 experiments. 

Once you have downloaded and organized input data for the modules you'd like to use and cloned the module registry to your local project work space, you can proceed to the next section that demonstrates how to configure and run a FACTS experiment using `facts-experiment-builder`. 

The rest of the examples in this page will demonstrate how to create and run a facts experiment called `my_first_experiment`. You can see the experiment configuration and execution files that are created by running the following commands in `./experiments/my_first_experiment/`. 

If you are new to FACTS and terms, we recommend pausing here and reviewing our [FACTS Glossary] page. It contains descriptions of terms that will be helpful to know in the following sections. 

## Create an experiment

Use the `feb setup-experiment` command like this: 
```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb setup-experiment \
--experiment-name my_first_experiment \
--climate-step fair-temperature \
--sealevel-step bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,kopp14-verticallandmotion,ssp-landwaterstorage \
--total-all-modules True \
--extremesealevel-step extremesealevel-pointsoverthreshold \
--pipeline-id aaa --scenario ssp126 --baseyear 2005 \
--pyear-start 2020 --pyear-end 2150 --pyear-step 10 \
--nsamps 1000 --location-file location.lst \
--module-specific-inputs /path/to/module/inputs \
--shared-inputs /path/to/shared/inputs
```
- Not all of these options must be passed to `setup-new-experiment`, only `--experiment-name` is required. Any fields that are not passed at the CLI must be manually added to the `experiment-config.yml` file that is created after running `setup-experiment`. 

You can see the full list of options by running `uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb setup-experiment --help`. 

>[!NOTE]
> You can see which modules are available to use in an experiment by running `uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main list-modules`.

If you included multiple modules at the sea-level step, you will see ClI prompts asking if you'd like to specify additional *workflows*. Workflows are collections of modules within an experiment that are summed to produce comprehensive distributions of projected future sea-level change - head to the [glossary] for more detail on this.

Once you've completed the workflows section, you'll see messages with information about the experiment and stating that an `experiment-config.yml` file has been written. Congratulations - you have just created a FACTS2 experiment! 

Inspect the experiment configuration file and ensure that all of the fields in the top section of required arguments are completed. For more detail, see our [Experiment configuration file overview](EXPERIMENT-CONFIG-OVERVIEW.md) page. 

## Run an experiment

In the previous section, we created an experiment with the `feb setup-experiment` command, which generated a file, `experiment-config.yml` in our experiment's sub-directory. If you read the overview of the experiment-config file, you'll know that this file acts as the core artifact that fully specifies the experiment. However, you'll notice that it doesn't actually have the information required to *run* an experiment. 

FACTS2 plans to offer multiple implementations to run experiments in different computational environments. For now, we only provide a [Docker Compose](https://docs.docker.com/compose/) implementation. If you don't have Docker installed on your machine, follow Docker's installation [instructions](https://docs.docker.com/get-started/get-docker/). 

facts-experiment-builder provides a command, `feb generate`, to generate an executable Docker Compose file from an `experiment-config.yml` that wil be used to actually run your experiment. The command writes the file, `experiment-compose.yml`, to your experiment's sub-directory just like `experiment-config.yml`. For more detail on the experiment compose file, see the [overview](EXPERIMENT-COMPOSE-OVERVIEW.md) page.

Create the file by specifying the name of the experiment:
```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb generate --experiment-name my_first_experiment
```

Inspect the compose file and when you are ready to run the experiment, execute it like this:
```shell
docker compose -f experiments/my_first_experiment/experiment-compose.yaml
```

**Not yet implemented: async-flow equivalent of `generate-compose`.**

## Features
facts-experiment-builder is a command line application with two main functions:

**`setup-new-experiment`**
Initialize a new experiment by calling this command and providing an experiment name and the modules (or pre-existing data) for each step. `facts-experiment-builder` creates a sub-directory to hold run files and outputs associated with this experiment. It also generates and prepopulates an `experiment-config.yaml` based on the arguments provided by the user. The user must then enter any remaining fields in `experiment-config.yaml` before it is considered complete.

Each step accepts either a module name or a path to pre-existing data:
- `--climate-step` / `--supplied-climate-step-data`: run a climate module or provide climate output directly
- `--sealevel-step` / `--supplied-totaled-sealevel-step-data`: run sealevel module(s) or provide sealevel output directly (totaling is automatically skipped when `--supplied-totaled-sealevel-step-data` is used)

```shell
Usage: setup-new-experiment [OPTIONS]

  Set up a new experiment with setup-new-experiment CLI command. This function
  includes a number of steps:

      - Creates a sub-directory in experiments/ for this experiment. Raises
      error if one already exists

      - Check that all required arguments were Received

      - Create a SkeletonExperiment object. This only includes information
      about which modules will be included in the experiment.

      - If facts-total passed, collects workflows w/ user prompts

Options:
  --experiment-name TEXT          Name of the experiment  [required]
  --climate-step TEXT             Name of the temperature module
  --supplied-climate-step-data PATH
                                  Path to data to use in place of running a
                                  module in the climate step of the
                                  experiment.
  --sealevel-step TEXT            Names of the sea level modules, separated by
                                  commas
  --supplied-totaled-sealevel-step-data PATH
                                  Path to pre-existing totaled sealevel data.
                                  Replaces running both the climate and
                                  sealevel steps.
  --total-all-modules BOOLEAN     If true, automatically creates a workflow
                                  that includes all specified sealevel
                                  modules. User may still choose to specify
                                  additional workflows.  [default: True]
  --extremesealevel-step TEXT     Name of the extreme sea level module (use
                                  'NONE' if no extreme sea level module)
  --pipeline-id TEXT              Pipeline ID
  --scenario TEXT                 Scenario
  --baseyear INTEGER              Base year
  --pyear-start INTEGER           Projection year start
  --pyear-end INTEGER             Projection year end
  --pyear-step INTEGER            Projection year step
  --nsamps INTEGER                Number of samples
  --location-file TEXT            Location file name
  --module-specific-inputs TEXT   Path to module-specific input data (written
                                  to experiment metadata)
  --shared-inputs TEXT            Path to shared input data (written to
                                  experiment metadata)
  --debug / --no-debug
  -h, --help                      Show this message and exit.
```

**`generate-compose`**
From a completed `experiment-config.yaml`, this command generates a Docker compose script that executes the experiment defined in the experiment metadata file. 

```shell
 uv run generate-compose --help                          
Usage: generate-compose [OPTIONS]

  Generate Docker Compose file from experiment metadata.

Options:
  --experiment-name TEXT     Name of the experiment (will look in experiments/
                             directory)  [required]
  --custom-output-path PATH  Output path for compose file. If not provided,
                             will use ../experiment_dir/experiment-
                             compose.yaml. If provided, must include full path
                             to file and use filename 'experiment-
                             compose.yaml'
  -h, --help                 Show this message and exit.
```

## Other experiment configurations 
---
You can bypass running a module at the climate step and instead pass your own data for this step that will be passed to the sea-level step. Below is an example of creating an experiment using pre-existing climate data instead of running a module at the climate step:
```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main setup-new-experiment \
--experiment-name toy_experiment_with_climate_data --scenario ssp585 \
--pyear-start 2020 --pyear-end 2100 --pyear-step 10 --baseyear 2005 --nsamps 1000 \
--supplied-climate-step-data /path/to/climate_data.nc \
--sealevel-step bamber19-icesheets,tlm-sterodynamics \
--extremesealevel-step extremesealevel-pointsoverthreshold
```

## Support

Source code is available online at https://github.com/fact-sealevel/facts-experiment-builder. This software is open source and available under the MIT license.

Please file issues in the issue tracker at https://github.com/fact-sealevel/facts-experiment-builder/issues.
