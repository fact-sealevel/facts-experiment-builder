# Quickstart Guide

This page contains instructions for getting started working with FACTS2. Configuring and running a FACTS2 experiment involves specifying modules to include in your experiment. This page includes instructions on initializing a workspace, downloading input data required to run different modules, and accessing the module registry.

 🚧 THIS PAGE IS UNDER CONSTRUCTION 🚧  
 Check back soon for updates.

## Workflow at a glance

1. **`feb init`** — initialize your workspace (creates `experiments/`, clones module registry)
2. **Download input data** — see section ii below
3. **`feb setup-experiment`** — configure an experiment and write `experiment-config.yaml`
4. **`feb generate-compose`** — generate the Docker Compose run script
5. **`docker compose ... up`** — run the experiment

---

## i. Initialize your workspace

Navigate to the directory where you will store FACTS2 experiments (e.g. `/Users/Desktop/projects/facts2_work`).

Run `feb init` to set up your project workspace:

```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb init
```

This single command:
1. Creates an `experiments/` subdirectory to hold all files and outputs associated with your experiments
2. Clones the [facts-module-registry](https://github.com/fact-sealevel/facts-module-registry) into your workspace
3. Writes a `.facts-workspace` marker file

It is safe to re-run on an already-initialized workspace — existing directories and files will not be overwritten.

---

## ii. Downloading module input data

This section describes how to download and organize input data for modules in the FACTS 2 ecosystem for use with `facts-experiment-builder`.

Input data can be stored anywhere on your machine — it does not need to live inside your workspace. The scripts below assume a standard layout with a `data/` directory inside your workspace root. If your data is stored elsewhere, adjust the paths accordingly and pass the correct paths to `feb setup-experiment` via `--module-specific-input-data` and `--shared-input-data`.

Run the following from your **workspace root**:

```shell
mkdir -p data/module_specific_input_data
mkdir -p data/shared_input_data
```

### Downloading shared input data

GRD fingerprint data (note: how this is handled is subject to change in the future):
```bash
curl -L https://zenodo.org/record/7478192/files/grd_fingerprints_data.tgz -o data/shared_input_data/grd_fingerprints_data.tgz
tar -xzf data/shared_input_data/grd_fingerprints_data.tgz -C data/shared_input_data
```

Location file (example with New York):
```bash
echo "New_York	12	40.70	-74.01" > data/shared_input_data/location.lst
```

### Downloading module-specific input data for all modules

The input data for each module is available at the Zenodo records shown below. You can also find this information in the README.md of each module in https://github.com/fact-sealevel.

> [!NOTE]
> For copy & paste scripts to download input data for individual modules, head to the [module-specific input data downloads](module_input_data_downloads.md) page.

```bash
mkdir -p data/module_specific_input_data/fair-temperature data/module_specific_input_data/fair2-climate data/module_specific_input_data/fittedismip-gris data/module_specific_input_data/bamber19-icesheets data/module_specific_input_data/deconto21-ais data/module_specific_input_data/ipccar5-glaciers data/module_specific_input_data/ipccar5-icesheets data/module_specific_input_data/larmip-ais data/module_specific_input_data/ssp-landwaterstorage data/module_specific_input_data/tlm-sterodynamics data/module_specific_input_data/ebm3-thermalexpansion

curl -L https://zenodo.org/record/7478192/files/fair_temperature_fit_data.tgz -o data/module_specific_input_data/fair-temperature/fair_temperature_fit_data.tgz
tar -xzf data/module_specific_input_data/fair-temperature/fair_temperature_fit_data.tgz -C data/module_specific_input_data/fair-temperature
curl -L https://zenodo.org/record/7478192/files/fair_temperature_preprocess_data.tgz -o data/module_specific_input_data/fair-temperature/fair_temperature_preprocess_data.tgz
tar -xzf data/module_specific_input_data/fair-temperature/fair_temperature_preprocess_data.tgz -C data/module_specific_input_data/fair-temperature

curl -L https://zenodo.org/records/11506798/files/fair2_climate_project_data.tgz -o data/module_specific_input_data/fair2-climate/fair2_climate_project_data.tgz
tar -xzf data/module_specific_input_data/fair2-climate/fair2_climate_project_data.tgz -C data/module_specific_input_data/fair2-climate

curl -L https://zenodo.org/record/7478192/files/FittedISMIP_icesheet_fit_data.tgz -o data/module_specific_input_data/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz
tar -xzf data/module_specific_input_data/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz -C data/module_specific_input_data/fittedismip-gris

curl -L https://zenodo.org/record/7478192/files/bamber19_icesheets_preprocess_data.tgz -o data/module_specific_input_data/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz
tar -xzf data/module_specific_input_data/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz -C data/module_specific_input_data/bamber19-icesheets

curl -L https://zenodo.org/record/7478192/files/deconto21_AIS_preprocess_data.tgz -o data/module_specific_input_data/deconto21-ais/deconto21_AIS_preprocess_data.tgz
tar -xzf data/module_specific_input_data/deconto21-ais/deconto21_AIS_preprocess_data.tgz -C data/module_specific_input_data/deconto21-ais

curl -L https://zenodo.org/record/7478192/files/ipccar5_glaciers_project_data.tgz -o data/module_specific_input_data/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz
tar -xzf data/module_specific_input_data/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz -C data/module_specific_input_data/ipccar5-glaciers

curl -L https://zenodo.org/record/7478192/files/ipccar5_icesheets_project_data.tgz -o data/module_specific_input_data/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz
tar -xzf data/module_specific_input_data/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz -C data/module_specific_input_data/ipccar5-icesheets

curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_fit_data.tgz -o data/module_specific_input_data/larmip-ais/larmip_icesheet_fit_data.tgz
tar -xzf data/module_specific_input_data/larmip-ais/larmip_icesheet_fit_data.tgz -C data/module_specific_input_data/larmip-ais
curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_project_data.tgz -o data/module_specific_input_data/larmip-ais/larmip_icesheet_project_data.tgz
tar -xzf data/module_specific_input_data/larmip-ais/larmip_icesheet_project_data.tgz -C data/module_specific_input_data/larmip-ais

curl -L https://zenodo.org/record/7478192/files/ssp_landwaterstorage_preprocess_data.tgz -o data/module_specific_input_data/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz
tar -xzf data/module_specific_input_data/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz -C data/module_specific_input_data/ssp-landwaterstorage

curl -L https://zenodo.org/record/7478192/files/tlm_sterodynamics_preprocess_data.tgz -o data/module_specific_input_data/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz
tar -xzf data/module_specific_input_data/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz -C data/module_specific_input_data/tlm-sterodynamics

curl -L https://zenodo.org/records/11506798/files/ebm3_thermal_expansion_data.tgz -o data/module_specific_input_data/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz
tar -xzf data/module_specific_input_data/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz -C data/module_specific_input_data/ebm3-thermalexpansion
```

You are now ready to start creating FACTS2 experiments! Head back to the facts-experiment-builder [README](../README.md#create-an-experiment) for an example of how to create a new experiment with `feb setup-experiment`.
