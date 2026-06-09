[![codecov](https://codecov.io/gh/fact-sealevel/facts-experiment-builder/branch/main/graph/badge.svg)](https://codecov.io/gh/fact-sealevel/facts-experiment-builder)

# facts-experiment-builder

> [!CAUTION]
> 🚧🚧 This is a prototype. It is likely to change in breaking ways, please don't rely on it in production and check back regularly for updates and new releases. This repo, including documentation, is still in draft form. If you encounter any issuse or have questions, feel free to raise an issue or email emarshall@rhg.com. 🚧🚧



## Overview
`facts-experiment-builder` (FEB) is a package for configuring and managing FACTS2 experiments. A FACTS2 experiment consists of running one or more modules from the [FACTS2 ecosystem](https://github.com/fact-sealevel). It has two key types of artifacts: an experiment configuration file, which represents the full, scientific specification of the experiment, and execution scripts that are used to run the experiment. If you are familiar with FACTS1, a FACTS2 `experiment-config.yaml` is similar to a `config.yaml` file that was used to define experiments in the previous framework. FEB offers a command line interface (CLI) with five main commands: 
- `feb init` to set up a workspace,
- `feb setup-experiment` to configure an experiment and write an experiment configuration file, 
- `feb generate-compose` to generate an executable experiment script from that configuration file, 
- `feb check-data` to verify that all expected module input files are present, and 
- `feb list-modules` to see all available modules in your registry. 

An experiment execution file is created with `feb generate-compose`. This contains all of the information required to run an experiment in a given execution environment. For now, we provide a Docker Compose implementation (`experiment-compose.yaml`). In the future, we plan to include an [Async-Flow](https://radical-cybertools.github.io/radical.asyncflow/) (`async-flow-experiment.py`) implementation.

>[!IMPORTANT]
> Experiment configuration files are not executable files. They only specify an experiment, while implementation files such as `experiment-compose.yaml` created by `generate-compose` function as execution scripts. 

## Outline 
This README is organized as follows:
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Create an experiment](#create-an-experiment)
- [Run an experiment](#run-an-experiment)
- [Features](#features)
- [Other experiment configurations](#other-experiment-configurations)
- [Support](#support)

Other important pages:
(some of these might move elsewhere within the facts org eventually, just here for now).
- [FEB Setup Guide](docs/SETUP.md)
- [Experiment config file overview](docs/EXPERIMENT-CONFIG-OVERVIEW.md)
- [Experiment compose file overview](docs/EXPERIMENT-COMPOSE-OVERVIEW.md)
- [FACTS Glossary](docs/FACTS_GLOSSARY.md)
- [Information for module contributors](docs/CONTRIBUTOR_DOCS.md)

---

## Requirements

- **[Docker](https://docs.docker.com/get-started/get-docker/)** — required to run experiments. Install Docker Desktop (Mac/Windows) or Docker Engine (Linux) before proceeding to the "Run an experiment" step.
- **A Python package manager** — to install and run FEB. We recommend [uv](https://docs.astral.sh/uv/getting-started/installation/) (see the Installation section below), but `pip` / `pipx` work equally well if you prefer them.
- **git** — required by `feb init` to clone the module registry.

---

## Installation

> [!NOTE]
> FEB is in early-stage development and is not yet published to PyPI. Until a PyPI release is available, the package is installed directly from GitHub as shown below.

To install FEB so you can type `feb <command>` directly:

```shell
# with uv (recommended)
uv tool install git+https://github.com/fact-sealevel/facts-experiment-builder@main

# with pipx
pipx install git+https://github.com/fact-sealevel/facts-experiment-builder@main

# with pip (into your active environment)
pip install git+https://github.com/fact-sealevel/facts-experiment-builder@main
```

Alternatively, [`uvx`](https://docs.astral.sh/uv/guides/tools/) can run FEB without a permanent install. This is useful if you want to try it out without adding it to your environment, but requires the full `uvx --from ...` prefix every time:

```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb <command>
```

The examples in this README use the full `uvx` form so they work without any prior installation. Once FEB is installed, replace `uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main` with just `feb`.

---

## Getting started

Before creating experiments you will need to initialize a workspace, download module input data, and verify it. The [Setup guide](docs/SETUP.md) walks through these steps. Once your data is in place, come back here to create and run an experiment.

If you are new to FACTS and the terms associated with it, we recommend reviewing the [FACTS Glossary](docs/FACTS_GLOSSARY.md) before proceeding.

The examples below demonstrate creating and running a FACTS experiment called `my_first_experiment`. Files for this experiment will be in `./experiments/my_first_experiment/`.

## Create an experiment

Use the `feb setup-experiment` command like this: 
```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb setup-experiment \
--experiment-name my_first_experiment \
--climate-step fair-temperature \
--sealevel-step bamber19-icesheets,deconto21-ais,fittedismip-gris,larmip-ais,ipccar5-glaciers,ipccar5-icesheets,tlm-sterodynamics,kopp14-verticallandmotion,ssp-landwaterstorage \
--extremesealevel-step extremesealevel-pointsoverthreshold \
--pipeline-id aaa --scenario ssp126 --baseyear 2005 \
--pyear-start 2020 --pyear-end 2150 --pyear-step 10 \
--nsamps 1000 --location-file location.lst \
--module-specific-input-data /path/to/module/inputs \
--shared-input-data /path/to/shared/inputs
```
- Not all of these options must be passed to `setup-experiment`.
- The required arguments are:
  - `--experiment-name`,
  - Either `--climate-step` (the module to run at the climate step) or `--supplied-climate-step-data` (data to bypass running a module at the climate step). 
-  Any fields that are not passed at the CLI must be manually added to the `experiment-config.yaml` file that is created after running `setup-experiment`. 

You can see the full list of options by running `uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb setup-experiment --help`. 

If you included multiple modules at the sea-level step, you will see CLI prompts asking if you'd like to specify additional *workflows*. Workflows are collections of modules within an experiment that are summed to produce comprehensive distributions of projected future sea-level change - head to the [glossary](docs/FACTS_GLOSSARY.md) for more detail on this.

Once you've completed the workflows section, you'll see messages with information about the experiment and stating that an `experiment-config.yaml` file has been written. Congratulations - you have just created a FACTS2 experiment! 

Inspect the experiment configuration file and ensure that all of the fields in the top section of required arguments are completed. For more detail, see our [experiment configuration file overview](docs/EXPERIMENT-CONFIG-OVERVIEW.md) page. 

## Run an experiment

In the previous section, we created an experiment with the `feb setup-experiment` command, which generated a file, `experiment-config.yaml`, in our experiment's sub-directory (`./experiments/my_first_experiment`). As stated above, the experiment configuration file acts as the core artifact that fully specifies the experiment, it does not actually *run* an experiment. 

FACTS2 plans to offer multiple implementations to run experiments in different computational environments. For now, we only provide a [Docker Compose](https://docs.docker.com/compose/) implementation. If you don't have Docker installed on your machine, follow Docker's installation [instructions](https://docs.docker.com/get-started/get-docker/). 

facts-experiment-builder provides a command, `feb generate-compose`, to generate an executable Docker Compose file from an `experiment-config.yaml` that wil be used to run your experiment. The command writes the file, `experiment-compose.yaml`, to your experiment's sub-directory just like `experiment-config.yaml`. For more detail on the experiment compose file, see the [overview](docs/EXPERIMENT-COMPOSE-OVERVIEW.md) page.

Create the file by specifying the name of the experiment:
```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb generate-compose --experiment-name my_first_experiment
```

Inspect the compose file and when you are ready to run the experiment, execute it like this:
```shell
docker compose -f experiments/my_first_experiment/experiment-compose.yaml up
```

**Not yet implemented: async-flow equivalent of `generate-compose`.**

## Features
facts-experiment-builder is a command line application with five main commands:

**`init`**
Initialize a FACTS workspace in the current directory. Creates the `experiments/` subdirectory, clones the module registry, and writes a `.facts-workspace` marker. Safe to re-run.

```shell
Usage: feb init [OPTIONS]

  Initialize a FACTS workspace in the current directory.

  Creates experiments/, clones the module registry, and writes a
  .facts-workspace marker file. Safe to re-run on an already-initialized
  workspace.

Options:
  --registry-url TEXT  Git URL of the facts-module-registry to clone.
                       [default: https://github.com/fact-sealevel/facts-module-registry.git]
  -h, --help           Show this message and exit.
```

>[!NOTE]
> After running `feb init`, you can see all available modules by running `feb list-modules`. This prints the names of all modules in your local `facts-module-registry` — these are the valid values for `--climate-step`, `--sealevel-step`, and `--extremesealevel-step`.
> ```shell
> uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb list-modules
> ```

**`setup-experiment`**
Initialize a new experiment by calling this command and providing an experiment name and the modules (or pre-existing data) for each step. `facts-experiment-builder` creates a sub-directory to hold run files and outputs associated with this experiment. It also generates and prepopulates an `experiment-config.yaml` based on the arguments provided by the user. The user must then enter any remaining fields in `experiment-config.yaml` before it is considered complete.

Each step accepts either a module name or a path to pre-existing data:
- `--climate-step` / `--supplied-climate-step-data`: run a climate module or provide climate output directly
- `--sealevel-step` / `--supplied-totaled-sealevel-step-data`: run sealevel module(s) or provide sealevel output directly (totaling is automatically skipped when `--supplied-totaled-sealevel-step-data` is used)

```shell
Usage: setup-experiment [OPTIONS]

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
  --location-file TEXT            Location file name (Must be in 'shared-
                                  input-data' directory).
  --module-specific-input-data TEXT
                                  Absolute path to module-specific input data
                                  to use in experiment.
  --shared-input-data TEXT        Absolute path to shared input data to use in
                                  experiment.
  --projection-scale [global|local|both]
                                  Projection scale for this experiment:
                                  'global', 'local', or 'both'.  [default:
                                  local]
  --module-regions TEXT           Specify regions for a module, format:
                                  module-name=REGION1,REGION2. Repeatable.
                                  Example: --module-regions
                                  emulandice2-glaciers=RGI01,RGI02
  --debug                         Enable debug logging globally.
  --debug-target TEXT             enable debug logging for a specific module
                                  only.
  -h, --help                      Show this message and exit.
```

**`generate-compose`**
From a completed `experiment-config.yaml`, this command generates a Docker compose script that executes the experiment defined in the experiment metadata file. 

```shell
Usage: feb generate-compose [OPTIONS]

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

**`list-modules`**
Lists all modules available in your local `facts-module-registry`. Use this to see the valid module names before running `feb setup-experiment`.

```shell
Usage: feb list-modules [OPTIONS]

  List all modules in the registry. These are all of the modules that can be
  included in experiments built with facts-experiment-builder.

Options:
  -h, --help  Show this message and exit.
```

**`check-data`**
Checks a data directory against expected module inputs from the registry. Scans `module_specific_input_data/` for downloaded modules and verifies that all expected input files are present. Also checks shared input data (`shared_input_data/`). Run this after downloading input data to catch missing or misnamed files before setting up an experiment.

```shell
Usage: feb check-data [OPTIONS]

  Check a FACTS data directory against expected module inputs.

  Scans module_specific_input_data/ for downloaded modules and verifies that
  all expected input files are present based on the module registry.

Options:
  --data-dir PATH                   Root data directory. Expects
                                    module_specific_input_data/ and
                                    shared_input_data/ subdirectories.
                                    [default: data]
  --module-specific-input-data PATH
                                    Path to module-specific input data
                                    directory. Overrides --data-dir derived
                                    path.
  --shared-input-data PATH          Path to shared input data directory.
                                    Overrides --data-dir derived path.
  -h, --help                        Show this message and exit.
```

## Other experiment configurations 
---
You can bypass running a module at the climate step and instead pass your own data for this step that will be passed to the sea-level step. Below is an example of creating an experiment using pre-existing climate data instead of running a module at the climate step:
```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb setup-experiment \
--experiment-name toy_experiment_with_climate_data --scenario ssp585 \
--pyear-start 2020 --pyear-end 2100 --pyear-step 10 --baseyear 2005 --nsamps 1000 \
--supplied-climate-step-data /path/to/climate_data.nc \
--sealevel-step bamber19-icesheets,tlm-sterodynamics \
--extremesealevel-step extremesealevel-pointsoverthreshold
```

 🚧 Check back soon for more. 🚧

## Support

Source code is available online at https://github.com/fact-sealevel/facts-experiment-builder. This software is open source and available under the MIT license.

Please file issues in the issue tracker at https://github.com/fact-sealevel/facts-experiment-builder/issues.
