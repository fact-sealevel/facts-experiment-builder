# Available Modules

All module names below are in kebab-case as used in CLI arguments. Config files use snake_case equivalents (e.g. `bamber19-icesheets` → `bamber19_icesheets_module.yaml`).

## Temperature

| Module name | Description |
|-------------|-------------|
| `fair-temperature` | FaIR simple climate model; provides temperature and ocean heat content forcing |

Use `NONE` as the temperature module if you are supplying pre-computed climate files directly.

## Sea Level

### Ice sheets — Antarctic Ice Sheet (AIS)

| Module name | Description |
|-------------|-------------|
| `bamber19-icesheets` | Bamber et al. (2019) expert elicitation for AIS contribution |
| `deconto21-ais` | DeConto et al. (2021) marine ice sheet model for AIS |
| `emulandice-ais` | emulatorlandice AIS contribution |
| `ipccar5-icesheets` | IPCC AR5 ice sheet contribution |
| `larmip-ais` | LARMIP-2 linear response model for AIS |

### Ice sheets — Greenland Ice Sheet (GrIS)

| Module name | Description |
|-------------|-------------|
| `emulandice-gris` | emulatorlandice GrIS contribution |
| `fittedismip-gris` | Fitted ISMIP6 emulator for GrIS contribution |

### Glaciers

| Module name | Description |
|-------------|-------------|
| `emulandice-glaciers` | emulatorlandice glacier contribution |
| `ipccar5-glaciers` | IPCC AR5 glacier contribution |

### Sterodynamics

| Module name | Description |
|-------------|-------------|
| `tlm-sterodynamics` | Thermal expansion and dynamic sea-level change |

### Vertical Land Motion

| Module name | Description |
|-------------|-------------|
| `kopp14-verticallandmotion` | Kopp (2014) vertical land motion |
| `nzinsargps-verticallandmotion` | InSAR/GPS-based vertical land motion for New Zealand |

### Land Water Storage

| Module name | Description |
|-------------|-------------|
| `ssp-landwaterstorage` | SSP-based land water storage contribution |

## Framework

| Module name | Description |
|-------------|-------------|
| `facts-total` | Sums sea-level contributions across modules and workflows to produce total sea-level projections |

Use `NONE` if no aggregation module is needed.

## Extreme Sea Level

| Module name | Description |
|-------------|-------------|
| `extremesealevel-pointsoverthreshold` | Extreme sea-level return periods using points-over-threshold method |

Use `NONE` if no extreme sea-level analysis is needed.

---

## Adding a new module

Place the module's `*_module.yaml` and optional `defaults_*.yml` in `src/facts_experiment_builder/resources/module_registry/<module-name>/`. The module will automatically be available to the CLI.
