# list-modules

Lists all modules currently available in the module registry.

## Usage

```shell
list-modules
```

## What it does

Prints the names of all modules that can be passed to `--temperature-module`, `--sealevel-modules`, `--framework-module`, or `--extremesealevel-module` when running `setup-new-experiment`.

Useful for checking what's available without consulting the docs, especially after adding new modules to the registry.

## Example output

```
Modules: ['bamber19-icesheets', 'deconto21-ais', 'emulandice-ais', 'emulandice-glaciers', 'emulandice-gris', 'extremesealevel-pointsoverthreshold', 'facts-total', 'fair-temperature', 'fittedismip-gris', 'ipccar5-glaciers', 'ipccar5-icesheets', 'kopp14-verticallandmotion', 'larmip-ais', 'nzinsargps-verticallandmotion', 'ssp-landwaterstorage', 'tlm-sterodynamics']
```

See [Available Modules](modules.md) for descriptions of each.
