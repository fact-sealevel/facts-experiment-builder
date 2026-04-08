# Adding a Module

Adding a new module requires two files in the module registry — a module YAML and an optional defaults YAML. No changes to the experiment builder code are needed.

!!! note
    Module YAMLs are currently maintained by hand in this repo. Eventually they will live with their corresponding containerized module repositories.

---

## 1. Create the registry entry

Add a directory for your module under:

```
src/facts_experiment_builder/resources/module_registry/<module-name>/
```

Module names use kebab-case (e.g. `my-new-module`). The directory should contain:

```
my-new-module/
  my_new_module_module.yaml      # required
  defaults_my_new_module.yml     # optional
```

---

## 2. Write the module YAML

See the [Module YAML Reference](module-yaml-reference.md) for a fully annotated example.

The module YAML describes your module's container image, command, and all arguments (inputs, outputs, options). Use an existing module as a reference — `bamber19-icesheets` is a good example of a module that uses a climate file, and `fair-temperature` is a good example of a temperature module.

### Top-level fields

```yaml
module_name: "my-new-module"           # kebab-case, must match directory name
container_image: "ghcr.io/org/my-new-module:1.0.0"
command: "main"
uses_climate_file: true                # true if this module consumes temperature output
climate_file_required: false           # true if the climate file is strictly required
```

### `arguments`

Arguments are grouped into four sections. They are passed to the container command in this order: `top_level` → `fingerprint_params` → `options` → `inputs` → `outputs`.

#### `top_level`

Parameters sourced from the experiment-level metadata (shared across all modules):

```yaml
arguments:
  top_level:
    - name: "pipeline-id"
      type: "str"
      source: "metadata.pipeline-id"
    - name: "nsamps"
      type: "int"
      source: "metadata.nsamps"
    - name: "scenario"
      type: "str"
      source: "metadata.scenario"
      transform: "scenario_name"   # optional: applies a name mapping transform
    - name: "pyear-start"
      type: "int"
      source: "metadata.pyear_start"
    - name: "pyear-end"
      type: "int"
      source: "metadata.pyear_end"
    - name: "pyear-step"
      type: "int"
      source: "metadata.pyear_step"
    - name: "baseyear"
      type: "int"
      source: "metadata.baseyear"
```

#### `fingerprint_params`

Include these if your module uses GRD fingerprint data or a location file:

```yaml
  fingerprint_params:
    - name: "fingerprint-dir"
      type: "str"
      source: "module_inputs.fingerprint_params.fingerprint_dir"
      mount:
        volume: "input"
        container_path: "/mnt/general_in"
    - name: "location-file"
      type: "str"
      source: "module_inputs.fingerprint_params.location_file"
      mount:
        volume: "input"
        container_path: "/mnt/general_in"
```

#### `options`

Module-specific parameters (not file paths):

```yaml
  options:
    - name: "my-param"
      type: "int"
      source: "module_inputs.options.my_param"
    - name: "optional-param"
      type: "int"
      source: "module_inputs.options.optional_param"
      optional: true
```

#### `inputs`

Input files. Set `external_volume: true` for files produced by another module (e.g. climate output):

```yaml
  inputs:
    - name: "climate-data-file"
      type: "file"
      source: "module_inputs.inputs.climate_data_file"
      mount:
        volume: "output"
        container_path: "/mnt/out"
        transform: "filename"
      external_volume: true          # this file comes from the temperature module's output
    - name: "my-input-file"
      type: "file"
      source: "module_inputs.inputs.my_input_file"
      mount:
        volume: "module_specific_input"
        container_path: "/mnt/module_specific_in"
```

#### `outputs`

Output files written by the module. Use `output_type: "global"` for global sea-level and `output_type: "local"` for local:

```yaml
  outputs:
    - name: "output-slr-file"
      type: "file"
      source: "module_inputs.outputs.output-slr-file"
      filename: "slr.nc"
      output_type: "global"
      mount:
        volume: "output"
        container_path: "/mnt/out"
        transform: "filename"
```

### `volumes`

Declare the Docker volume mounts. Standard volume names are `module_specific_input`, `general_input`, and `output`:

```yaml
volumes:
  module_specific_input:
    host_path: "module_inputs.input_paths.module_specific_input_dir"
    container_path: "/mnt/module_specific_in"
  general_input:
    host_path: "module_inputs.input_paths.general_input_dir"
    container_path: "/mnt/general_in"
  output:
    host_path: "module_inputs.output_paths.output_dir"
    container_path: "/mnt/out"
```

---

## 3. Write the defaults YAML (optional)

The defaults YAML pre-populates `options` and `inputs` in `experiment-metadata.yml` when a user runs `setup-new-experiment`. If your module has sensible defaults, add them here so users don't have to look them up.

```yaml
# defaults_my_new_module.yml

options:
  my_param: 1
  optional_param: 50

inputs:
  my_input_file: "my_default_input.mat"
```

---

## 4. Verify

Check that the module is discovered by the registry:

```shell
uv run list-modules
```

Your module name should appear in the output. Then test it end-to-end with a minimal `setup-new-experiment` call:

```shell
uv run setup-new-experiment \
  --experiment-name test_my_module \
  --temperature-module NONE \
  --sealevel-modules my-new-module \
  --framework-module NONE \
  --extremesealevel-module NONE
```
