# Module-specific input data 

This page holds bash text that can be used to download input data for individual modules in the FACTS2 ecosystem. Run these commands from `./data`.

### fair-temperature

```bash
mkdir -p module_specific_input_data/fair-temperature
curl -L https://zenodo.org/record/7478192/files/fair_temperature_fit_data.tgz -o module_specific_input_data/fair-temperature/fair_temperature_fit_data.tgz
tar -xzf module_specific_input_data/fair-temperature/fair_temperature_fit_data.tgz -C module_specific_input_data/fair-temperature
curl -L https://zenodo.org/record/7478192/files/fair_temperature_preprocess_data.tgz -o module_specific_input_data/fair-temperature/fair_temperature_preprocess_data.tgz
tar -xzf module_specific_input_data/fair-temperature/fair_temperature_preprocess_data.tgz -C module_specific_input_data/fair-temperature
```

### fair2-climate

```bash
mkdir -p module_specific_input_data/fair2-climate
curl -L https://zenodo.org/records/11506798/files/fair2_climate_project_data.tgz -o module_specific_input_data/fair2-climate/fair2_climate_project_data.tgz
tar -xzf module_specific_input_data/fair2-climate/fair2_climate_project_data.tgz -C module_specific_input_data/fair2-climate
```

### fittedismip-gris

```bash
mkdir -p module_specific_input_data/fittedismip-gris
curl -L https://zenodo.org/record/7478192/files/FittedISMIP_icesheet_fit_data.tgz -o module_specific_input_data/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz
tar -xzf module_specific_input_data/fittedismip-gris/FittedISMIP_icesheet_fit_data.tgz -C module_specific_input_data/fittedismip-gris
```

### bamber19-icesheets

```bash
mkdir -p module_specific_input_data/bamber19-icesheets
curl -L https://zenodo.org/record/7478192/files/bamber19_icesheets_preprocess_data.tgz -o module_specific_input_data/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz
tar -xzf module_specific_input_data/bamber19-icesheets/bamber19_icesheets_preprocess_data.tgz -C module_specific_input_data/bamber19-icesheets
```

### deconto21-ais

```bash
mkdir -p module_specific_input_data/deconto21-ais
curl -L https://zenodo.org/record/7478192/files/deconto21_AIS_preprocess_data.tgz -o module_specific_input_data/deconto21-ais/deconto21_AIS_preprocess_data.tgz
tar -xzf module_specific_input_data/deconto21-ais/deconto21_AIS_preprocess_data.tgz -C module_specific_input_data/deconto21-ais
```

### ipccar5-glaciers

```bash
mkdir -p module_specific_input_data/ipccar5-glaciers
curl -L https://zenodo.org/record/7478192/files/ipccar5_glaciers_project_data.tgz -o module_specific_input_data/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz
tar -xzf module_specific_input_data/ipccar5-glaciers/ipccar5_glaciers_project_data.tgz -C module_specific_input_data/ipccar5-glaciers
```

### ipccar5-icesheets

```bash
mkdir -p module_specific_input_data/ipccar5-icesheets
curl -L https://zenodo.org/record/7478192/files/ipccar5_icesheets_project_data.tgz -o module_specific_input_data/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz
tar -xzf module_specific_input_data/ipccar5-icesheets/ipccar5_icesheets_project_data.tgz -C module_specific_input_data/ipccar5-icesheets
```

### larmip-ais

```bash
mkdir -p module_specific_input_data/larmip-ais
curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_fit_data.tgz -o module_specific_input_data/larmip-ais/larmip_icesheet_fit_data.tgz
tar -xzf module_specific_input_data/larmip-ais/larmip_icesheet_fit_data.tgz -C module_specific_input_data/larmip-ais
curl -L https://zenodo.org/record/7478192/files/larmip_icesheet_project_data.tgz -o module_specific_input_data/larmip-ais/larmip_icesheet_project_data.tgz
tar -xzf module_specific_input_data/larmip-ais/larmip_icesheet_project_data.tgz -C module_specific_input_data/larmip-ais
```

### ssp-landwaterstorage

```bash
mkdir -p module_specific_input_data/ssp-landwaterstorage
curl -L https://zenodo.org/record/7478192/files/ssp_landwaterstorage_preprocess_data.tgz -o module_specific_input_data/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz
tar -xzf module_specific_input_data/ssp-landwaterstorage/ssp_landwaterstorage_preprocess_data.tgz -C module_specific_input_data/ssp-landwaterstorage
```

### tlm-sterodynamics

```bash
mkdir -p module_specific_input_data/tlm-sterodynamics
curl -L https://zenodo.org/record/7478192/files/tlm_sterodynamics_preprocess_data.tgz -o module_specific_input_data/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz
tar -xzf module_specific_input_data/tlm-sterodynamics/tlm_sterodynamics_preprocess_data.tgz -C module_specific_input_data/tlm-sterodynamics
```

### ebm3-thermalexpansion

```bash
mkdir -p module_specific_input_data/ebm3-thermalexpansion
curl -L https://zenodo.org/records/11506798/files/ebm3_thermal_expansion_data.tgz -o module_specific_input_data/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz
tar -xzf module_specific_input_data/ebm3-thermalexpansion/ebm3_thermal_expansion_data.tgz -C module_specific_input_data/ebm3-thermalexpansion
```
