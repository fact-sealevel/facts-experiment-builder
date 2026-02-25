# facts-experiment-builder

## Overview
This is a prototype of a package for configuring and managing FACTS 2 experiments. A FACTS 2 experiment consists of running one or more modules from the FACTS 2 ecosystem. It produces sets of one or more distributions of projected future sea-level rise and/or future extreme sea-level events. FACTS 2 modules represent different physical processes. When run in the context of an experiment, they contribute to comprehensive estimates of future sea-level change under specified conditions.

A FACTS 2 experiment usually has a set of specified 'top-level parameters' that apply across all of the modules in the experiment. These can include the number of samples to draw (`nsamps`), the emissions scenario (`scenario`), the start and stop year of projections (`pyear-start`, `pyear-end`) and the temporal resolution of projections (`pyear-step`). Within an experiment, one can define multiple 'workflows`, these represent different combinations of sea-level modules to be summed to produce output distributions of projected future sea level rise. 

Because modules in the FACTS ecosystem represent varied and distinct physical processes and draw from a range of scientific and computational approaches, they are stored as individual, containerized applications with distinct computational environments. `facts-experiment-builder` acts as the framework layer to encapsulate individual experiments and to coordinate orchestration of these modules in a way that satisfies scientific requirements and computational limitations. 

This package centers around physical artifacts, YAML files, and core in-memory representations of the artifacts. For example, an experiment is abstractly defined as a set of parameters, a collection of modules, and a list of workflows. This is serialized as an `experiment-metadata.yml` file and represented in-memory by the `FactsExperiment` class. Each containerized module application has a corresponding `module_name_module.yaml` file (note: currently located in this repo, eventually will live with modules). This represents all of the inputs, outputs, and parameters used to specify that module as well as other critical metadata. In memory, this is stored as an object of the `FactsModule` class. To run a FACTS 2 experiment, we need more than the abstract information stored in an `experiment-metadata.yml`. `facts-experiment-builder` plans to offer implementations for multiple execution environments, with an experiment's `experiment-metadata.yml` remainining the underlying source of 'truth' about the experiment. From here, run files can be generated for specific execution environments such as Docker (`experiment-compose.yml` and Async-Flow (`async-flow-experiment.py`, **not yet implemented**).

## Features
This is a command line application with two main functions:

**`setup-new-experiment`**
Initialize a new experiment by calling this command and providing an experiment name and the modules that will be included in the experiment. `facts-experiment-builder` creates a sub-directory to hold run files and outputs associated with this experiment. It also generates and prepopulates a `experiment-metadata.yml` based on the arguments provided by the user. **The user must then enter the remaining fields in `experiment-metadata.yml` before it is considered complete.

**`generate-compose`**
From a completed `experiment-metadata.yml`, this command generates a Docker compose script that executes the experiment defined in the experiment metadata file. 

## Example
Warning: it is very rough and incomplete! 
with the example experiment provided below, you should be able to run the two steps, `uv run setup-new-experiment` and `uv run generate compose`, and then successfully execute the docker compose file to run the experiment.

### Steps to run:
#### Setup:
1. Start from your project root dir. For now, the experiment builder assumes you have an experiments sub-directory in this location. so something like...
```shell
mkdir fresh_facts_project
cd fresh_facts_project
mkdir experiments
```
2. experiment builder assumes you have facts input data downloaded (somewhere on your machine) and separated into module-specific input data and general input data.
- `module_specific_inputs` (or whatever it is called on your machine) should have a sub-directory for each FACTS module with the directory name matching the module name. ie.
```shell
module_specific_input_data/               
bamber19-icesheets                
caron18                           
deconto21-ais                            
fair-temperature                 
fair2-climate                    
fittedismip-gris 
...               
```
- have a separate `general_input_data` that contains `location.lst` and GRD fingerprint data. 
```shell
general_input_data/
location.lst
fingerprint_region_map.csv
FPRINT
```

#### 2. Create an experiment via CLI
- at a minimum, this entails specifying:
     - `experiment-name`
     - `temperature-module` (if using. note: will be renamed to climate-step)
     - `sealevel-modules`
- optionally, can also include `--pipeline-id`, `--scenario`, `--pyear-start`, `--pyear-end`, `--pyear-step`, `--baseyear`, `--nsamps`, `--seed`
Example:
```shell
uv run setup-new-experiment --experiment-name test_experiment --temperature-module fair-temperature --sealevel-modules bamber19-icesheets,deconto21-ais,fittedismip-gris,ipccar5-glaciers,ipccar5-icesheets,kopp14-verticallandmotion,nzinsargps-verticallandmotion,tlm-sterodynamics --scenario ssp585 --baseyear 2005 --pipeline-id aaa --pyear-start 2020 --pyear-end 2150 --pyear-step 10 --nsamps 100 --seed 1234
```
- This command: 
     - makes a sub-directory in experiments with the supplied `--experiment-name` 
     - creates and partially pre-populates an `experiment-metadata.yml`. this is equivalent to a facts1 experiment `config.yml`. it is meant to be an abstract (run-environment agnostic), self-describing specification of the full experiment
     - `experiment-metadata.yml` is prepopulated based on the arguments you supply and the modules you specified
3. Manually enter two fields in the experiment metadata yml and review
- If passed at the `uv run setup-new-experiment` step, values for `scenario`,`pyear-start/stop/step`,etc. will be prepopulated. if not, specify them here
- You must specify two things:
     - the path to the module specific input data on your machine (ie. `~/Desktop/facts_data/module_specific_inputs`)
     - the path to the general input data on your machine (ie. `~/Desktop/facts_data/general_inputs`)
- You shouldn't need to make any more edits to this file but you can review to see the full experiment specification before generating a compose file.
- 
#### 3. Generate docker compose file via CLI
Example:
```uv run generate-compose --experiment-name test_experiment```
- Produces a docker compose file, `experiment-compose.yml` in the experiment sub-directory. 
- this is the docker implementation of the abstract experiment specified by `experiment-metadata.yml`

Then,
- inspect the compose file
- run experiment like (assuming from project root) `docker compose -f experiments/experiment_name/experiment-compose.yaml up`


### Notes
More in the weeds notes on internals
`experiment-metadata.yml` and `*_modul.yaml` files represent artifacts for experiments and modules, respectively. In contrast, `experiment-compose.yml` is an executable implementation of an experiment. To handle the various translations between these states and entities, we define domain types and adapters to pass information between them. `FactsModule` represents the abstraction of a module, independent of any experiment. `ModuleExperimentSpec` holds the information about a module that is required for that module's section of a `experiment-metadata.yml`. Similarly, `ModuleServiceSpec` holds information about a module that is required for that module's section of a `experiment-metadata.yml`. 


 This is still very much in progress/rough but this much should be working. will keep making updates to fix issues described above and expand functionality/coverage. 
