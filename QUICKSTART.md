# Quickstart Guide

This page contains instructions for getting started working with FACTS2. Configuring and running a FACTS2 experiment involves specifying modules to include in your experiment. This page includes instructions on downloading input data required to run different modules and accessing the module-registry, this registry acts as the interface between the FACTS2 module ecosystem and the facts-experiment-builder.

 🚧 THIS PAGE IS UNDER CONSTRUCTION 🚧
 Check back soon for updates.
 
## i. Downloading module input data

This section describes how to download and organize input data for modules in the FACTS 2 ecosystem for use with `facts-experiment-builder`.

### Setup directories

Run these commands from the directory where you want to store the data. All download commands below use relative paths from that same location.

```shell
mkdir module_specific_inputs
mkdir shared_input_data
```

When running `setup-new-experiment`, pass the paths to these directories via `--module-specific-inputs` and `--shared-inputs`.

### Shared input data

GRD fingerprint data (note- how this is handled is subject to change in the future. this is most likely a temporary solution)
```bash
curl -L https://zenodo.org/record/7478192/files/grd_fingerprints_data.tgz -o shared_input_data/grd_fingerprints_data.tgz
tar -xzf shared_input_data/grd_fingerprints_data.tgz -C shared_input_data
```
Location file:
```bash
echo "New_York	12	40.70	-74.01" > shared_input_data
```

### Downloading module-specific input data for all modules

The input data for each module is available at the Zenodo records shown below. You can also find this information in the README.md of each module in https://github.com/fact-sealevel.

> [!NOTE]
> For copy & paste scripts to download input data for individual modules, head to the [module-specific input data downloads](module_input_data_downloads.md) page. 

```bash
mkdir -p module_specific_inputs/fair-temperature module_specific_inputs/fair2-climate module_specific_inputs/fittedismip-gris module_specific_inputs/bamber19-icesheets module_specific_inputs/deconto21-ais module_specific_inputs/ipccar5-glaciers module_specific_inputs/ipccar5-icesheets module_specific_inputs/larmip-ais module_specific_inputs/ssp-landwaterstorage module_specific_inputs/tlm-sterodynamics module_specific_inputs/ebm3-thermalexpansion

curl -L https://zenodo.org/record/7478192/files/grd_fingerprints_data.tgz -o shared_input_data/grd_fingerprints_data.tgz
tar -xzf shared_input_data/grd_fingerprints_data.tgz -C shared_input_data
echo "New_York	12	40.70	-74.01" > shared_input_data

curl -L https://zenodo.org/record/7478192/files/fair_temperature_fit_data.tgz -o module_specific_inputs/fair-temperature/fair_temperature_fit_data.tgz
tar -xzf module_specific_inputs/fair-temperature/fair_temperature_fit_data.tgz -C module_specific_inputs/fair-temperature
curl -L https://zenodo.org/record/7478192/files/fair_temperature_preprocess_data.tgz -o module_specific_inputs/fair-temperature/fair_temperature_preprocess_data.tgz
tar -xzf module_specific_inputs/fair-temperature/fair_temperature_preprocess_data.tgz -C module_specific_inputs/fair-temperature

curl -L https://zenodo.org/records/11506798/files/fair2_climate_project_data.tgz -o module_specific_inputs/fair2-climate/fair2_climate_project_data.tgz
tar -xzf module_specific_inputs/fair2-climate/fair2_climate_project_data.tgz -C module_specific_inputs/fair2-climate

curl -L https://zenodo.org/record/7478192/files/FittedISMIP_icesheet_fit_data.tgz -o module_specific_inputs/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz
tar -xzf module_specific_inputs/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz -C module_specific_inputs/fittedismip-gris

curl -L https://zenodo.org/record/7478192/files/bamber19_icesheets_preprocess_data.tgz -o module_specific_inputs/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz
tar -xzf module_specific_inputs/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz -C module_specific_inputs/bamber19-icesheets

curl -L https://zenodo.org/record/7478192/files/deconto21_AIS_preprocess_data.tgz -o module_specific_inputs/deconto21-ais/deconto21_AIS_preprocess_data.tgz
tar -xzf module_specific_inputs/deconto21-ais/deconto21_AIS_preprocess_data.tgz -C module_specific_inputs/deconto21-ais

curl -L https://zenodo.org/record/7478192/files/ipccar5_glaciers_project_data.tgz -o module_specific_inputs/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz
tar -xzf module_specific_inputs/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz -C module_specific_inputs/ipccar5-glaciers

curl -L https://zenodo.org/record/7478192/files/ipccar5_icesheets_project_data.tgz -o module_specific_inputs/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz
tar -xzf module_specific_inputs/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz -C module_specific_inputs/ipccar5-icesheets

curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_fit_data.tgz -o module_specific_inputs/larmip-ais/larmip_icesheet_fit_data.tgz
tar -xzf module_specific_inputs/larmip-ais/larmip_icesheet_fit_data.tgz -C module_specific_inputs/larmip-ais
curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_project_data.tgz -o module_specific_inputs/larmip-ais/larmip_icesheet_project_data.tgz
tar -xzf module_specific_inputs/larmip-ais/larmip_icesheet_project_data.tgz -C module_specific_inputs/larmip-ais

curl -L https://zenodo.org/record/7478192/files/ssp_landwaterstorage_preprocess_data.tgz -o module_specific_inputs/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz
tar -xzf module_specific_inputs/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz -C module_specific_inputs/ssp-landwaterstorage

curl -L https://zenodo.org/record/7478192/files/tlm_sterodynamics_preprocess_data.tgz -o module_specific_inputs/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz
tar -xzf module_specific_inputs/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz -C module_specific_inputs/tlm-sterodynamics

curl -L https://zenodo.org/records/11506798/files/ebm3_thermal_expansion_data.tgz -o module_specific_inputs/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz
tar -xzf module_specific_inputs/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz -C module_specific_inputs/ebm3-thermalexpansion
```

## ii. Cloning module registry

1. Setup your project workspace

- Navigate to your project workspace where you will store FACTS2 experiments (ie. `/Users/Desktop/projects/facts2_work`). 

- Create an `experiments/` sub-directory. This will hold all files associated with experiments as well as data produced from experiment runs. 

```shell
mkdir experiments
```

2. Clone the module repository

From this location, clone the [facts-module-registry](https://github.com/fact-sealevel/facts-module-registry) repository:

```
git clone git@github.com:fact-sealevel/facts-module-registry.git
```

You are now ready to start creating FACTS2 experiments! Head back to the facts-experiment-builder [documentation](README.md) for an example of how to create a new experiment with `setup-new-experiment`.
