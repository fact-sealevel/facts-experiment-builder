# Setup

This page describes how to download and organize input data for modules in the FACTS 2 ecosystem for use with `facts-experiment-builder`.

>[!ATTENTION]
> This is a temporary approach. A future version will have a more detailed/automated method for downloading and organizing input data (maybe).

## Setup directories

Run these commands from the directory where you want to store the data. All download commands below use relative paths from that same location.

```shell
mkdir module_specific_inputs
mkdir general_input_data
```

When running `setup-new-experiment`, pass the paths to these directories via `--module-specific-inputs` and `--general-inputs`.

## Downloading the data

The input data for each module is available at the following Zenodo records. You can also find this information in the README.md of each module in https://github.com/fact-sealevel.

### Download all modules at once

```bash
mkdir -p module_specific_inputs/fair-temperature module_specific_inputs/fair2-climate module_specific_inputs/fittedismip-gris module_specific_inputs/bamber19-icesheets module_specific_inputs/deconto21-ais module_specific_inputs/ipccar5-glaciers module_specific_inputs/ipccar5-icesheets module_specific_inputs/larmip-ais module_specific_inputs/ssp-landwaterstorage module_specific_inputs/tlm-sterodynamics module_specific_inputs/ebm3-thermalexpansion

curl -L https://zenodo.org/record/7478192/files/grd_fingerprints_data.tgz -o general_input_data/grd_fingerprints_data.tgz
tar -xzf general_input_data/grd_fingerprints_data.tgz -C general_input_data

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

### Download modules individually

Each block below can be copied and run independently from the directory containing `module_specific_inputs/`.

### General input data

```bash
curl -L https://zenodo.org/record/7478192/files/grd_fingerprints_data.tgz -o general_input_data/grd_fingerprints_data.tgz
tar -xzf general_input_data/grd_fingerprints_data.tgz -C general_input_data
```

> [!NOTE]
> A `location.lst` file is also required in `general_input_data`.

### fair-temperature

```bash
mkdir -p module_specific_inputs/fair-temperature
curl -L https://zenodo.org/record/7478192/files/fair_temperature_fit_data.tgz -o module_specific_inputs/fair-temperature/fair_temperature_fit_data.tgz
tar -xzf module_specific_inputs/fair-temperature/fair_temperature_fit_data.tgz -C module_specific_inputs/fair-temperature
curl -L https://zenodo.org/record/7478192/files/fair_temperature_preprocess_data.tgz -o module_specific_inputs/fair-temperature/fair_temperature_preprocess_data.tgz
tar -xzf module_specific_inputs/fair-temperature/fair_temperature_preprocess_data.tgz -C module_specific_inputs/fair-temperature
```

### fair2-climate

```bash
mkdir -p module_specific_inputs/fair2-climate
curl -L https://zenodo.org/records/11506798/files/fair2_climate_project_data.tgz -o module_specific_inputs/fair2-climate/fair2_climate_project_data.tgz
tar -xzf module_specific_inputs/fair2-climate/fair2_climate_project_data.tgz -C module_specific_inputs/fair2-climate
```

### fittedismip-gris

```bash
mkdir -p module_specific_inputs/fittedismip-gris
curl -L https://zenodo.org/record/7478192/files/FittedISMIP_icesheet_fit_data.tgz -o module_specific_inputs/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz
tar -xzf module_specific_inputs/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz -C module_specific_inputs/fittedismip-gris
```

### bamber19-icesheets

```bash
mkdir -p module_specific_inputs/bamber19-icesheets
curl -L https://zenodo.org/record/7478192/files/bamber19_icesheets_preprocess_data.tgz -o module_specific_inputs/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz
tar -xzf module_specific_inputs/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz -C module_specific_inputs/bamber19-icesheets
```

### deconto21-ais

```bash
mkdir -p module_specific_inputs/deconto21-ais
curl -L https://zenodo.org/record/7478192/files/deconto21_AIS_preprocess_data.tgz -o module_specific_inputs/deconto21-ais/deconto21_AIS_preprocess_data.tgz
tar -xzf module_specific_inputs/deconto21-ais/deconto21_AIS_preprocess_data.tgz -C module_specific_inputs/deconto21-ais
```

### ipccar5-glaciers

```bash
mkdir -p module_specific_inputs/ipccar5-glaciers
curl -L https://zenodo.org/record/7478192/files/ipccar5_glaciers_project_data.tgz -o module_specific_inputs/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz
tar -xzf module_specific_inputs/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz -C module_specific_inputs/ipccar5-glaciers
```

### ipccar5-icesheets

```bash
mkdir -p module_specific_inputs/ipccar5-icesheets
curl -L https://zenodo.org/record/7478192/files/ipccar5_icesheets_project_data.tgz -o module_specific_inputs/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz
tar -xzf module_specific_inputs/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz -C module_specific_inputs/ipccar5-icesheets
```

### larmip-ais

```bash
mkdir -p module_specific_inputs/larmip-ais
curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_fit_data.tgz -o module_specific_inputs/larmip-ais/larmip_icesheet_fit_data.tgz
tar -xzf module_specific_inputs/larmip-ais/larmip_icesheet_fit_data.tgz -C module_specific_inputs/larmip-ais
curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_project_data.tgz -o module_specific_inputs/larmip-ais/larmip_icesheet_project_data.tgz
tar -xzf module_specific_inputs/larmip-ais/larmip_icesheet_project_data.tgz -C module_specific_inputs/larmip-ais
```

### ssp-landwaterstorage

```bash
mkdir -p module_specific_inputs/ssp-landwaterstorage
curl -L https://zenodo.org/record/7478192/files/ssp_landwaterstorage_preprocess_data.tgz -o module_specific_inputs/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz
tar -xzf module_specific_inputs/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz -C module_specific_inputs/ssp-landwaterstorage
```

### tlm-sterodynamics

```bash
mkdir -p module_specific_inputs/tlm-sterodynamics
curl -L https://zenodo.org/record/7478192/files/tlm_sterodynamics_preprocess_data.tgz -o module_specific_inputs/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz
tar -xzf module_specific_inputs/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz -C module_specific_inputs/tlm-sterodynamics
```

### ebm3-thermalexpansion

```bash
mkdir -p module_specific_inputs/ebm3-thermalexpansion
curl -L https://zenodo.org/records/11506798/files/ebm3_thermal_expansion_data.tgz -o module_specific_inputs/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz
tar -xzf module_specific_inputs/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz -C module_specific_inputs/ebm3-thermalexpansion
```
