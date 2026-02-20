# facts-experiment-builder

This is a prototype of configuring and managing facts v2 experiments. 

Warning: it is very rough and incomplete! 
## Overview

### Example
(copy-pasting for now from old PR comment): 
with the provided example experiment below, you should be able to run the two steps, `uv run setup-new-experiment` and `uv run generate compose`, and then successfully execute the docker compose file to run the experiment.

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

 This is still very much in progress/rough but this much should be working. will keep making updates to fix issues described above and expand functionality/coverage. 
