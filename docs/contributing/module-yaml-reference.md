# Module YAML Reference

Every module in the registry is described by a YAML file. This page walks through a complete example — `bamber19-icesheets` — with annotations on each field.

The file has two logical sections with different audiences:

- **[Top section](#top-section-what-you-configure)** — fields you set when registering a new module: the container image, entrypoint, and a few flags. This is what you are responsible for getting right.
- **[Arguments & volumes](#arguments-volumes-for-reference)** — the full specification of how every argument and file path is wired together. This is generated/verified against the module's actual CLI interface. Editing it without a thorough understanding of how the adapter layer resolves arguments can break experiment generation in subtle ways.

---

## Top section — what you configure

<div class="annotate" markdown="1">
``` yaml
module_name: "bamber19-icesheets" # (1)!
container_image: "ghcr.io/fact-sealevel/bamber19-icesheets:0.1.0" # (2)!
uses_climate_file: true # (3)!
climate_file_required: false # (4)!
command: "main" # (5)!
```
</div>

1. The canonical module name in **kebab-case**. Must match the registry directory name and is what users pass to `--sealevel-modules` on the CLI.
2. The fully-qualified Docker image. Pin to a specific tag — avoid `latest` so experiment runs are reproducible.
3. Set to `true` if this module consumes the temperature module's output (e.g. a `climate.nc` file). When `true`, the adapter automatically adds a `depends_on` for the temperature service in the compose file.
4. Set to `true` if the climate file is _strictly_ required and the run should fail without it. Set to `false` to allow the module to run without one (e.g. if it has an internal fallback).
5. The entrypoint command inside the container. `"main"` is the convention for FACTS modules — the compose writer strips this when building the command string.

---

## Arguments & volumes — for reference

!!! warning "Treat this section as read-only unless you know what you're doing"
    The fields below wire each argument to its source in `experiment-metadata.yml` and define how files are mounted into the container. They are validated by the adapter layer at compose-generation time. Changing argument names, sources, or mount paths without a matching change to the module container will produce broken compose files or silent mis-configurations.

    If you are adding a **new** module, model this section closely on an existing one and verify with `uv run generate-compose` before opening a PR.

<div class="annotate" markdown="1">
``` yaml
arguments:

  top_level: # (1)!
    - name: "pipeline-id"
      type: "str"
      source: "metadata.pipeline-id" # (2)!
    - name: "nsamps"
      type: "int"
      source: "metadata.nsamps"
    - name: "rngseed"
      type: "int"
      source: "metadata.seed"
    - name: "scenario"
      type: "str"
      source: "metadata.scenario"
      transform: "scenario_name" # (3)!
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

  options: # (4)!
    - name: "replace"
      type: "int"
      source: "module_inputs.options.replace"
    - name: "chunksize"
      type: "int"
      source: "module_inputs.options.chunksize"
      optional: true # (5)!

  fingerprint_params: # (6)!
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

  inputs: # (7)!
    - name: "climate-data-file"
      type: "file"
      source: "module_inputs.inputs.climate_data_file"
      mount:
        volume: "output"
        container_path: "/mnt/out"
        transform: "filename" # (8)!
      external_volume: true # (9)!
    - name: "slr-proj-mat-file"
      type: "file"
      source: "module_inputs.inputs.slr_proj_mat_file"
      mount:
        volume: "module_specific_input"
        container_path: "/mnt/module_specific_in"
    - name: "fingerprint-dir"
      type: "str"
      source: "module_inputs.inputs.fingerprint_dir"
      mount:
        volume: "general_input"
        container_path: "/mnt/general_in"
    - name: "location-file"
      type: "file"
      source: "module_inputs.inputs.location_file"
      mount:
        volume: "general_input"
        container_path: "/mnt/general_in"

  outputs: # (10)!
    - name: "output-AIS-gslr-file"
      type: "file"
      source: "module_inputs.outputs.output-AIS-gslr-file"
      filename: "AIS-gslr.nc"
      output_type: "global" # (11)!
      mount:
        volume: "output"
        container_path: "/mnt/out"
        transform: "filename"
    - name: "output-AIS-lslr-file"
      type: "file"
      source: "module_inputs.outputs.output-AIS-lslr-file"
      filename: "AIS-lslr.nc"
      output_type: "local" # (12)!
      mount:
        volume: "output"
        container_path: "/mnt/out"
        transform: "filename"
    # ... remaining output files follow the same pattern

volumes: # (13)!
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
</div>

1. Parameters sourced from the **experiment level** — shared across every module in the run. The values come from `experiment-metadata.yml`'s top-level section. You should not need to change these for a typical module.
2. `source` is a dot-separated path resolved against the experiment context. `metadata.*` keys come from the top-level experiment metadata; `module_inputs.*` keys come from the module's own section in the metadata file.
3. An optional transform applied before the value is written to the compose command. `"scenario_name"` maps scenario strings for modules that expect a different naming convention (see `core/transforms.py`).
4. Module-specific parameters that are _not_ file paths — things like sample counts, flags, or algorithm settings. Values are populated from the module's section in `experiment-metadata.yml`, and defaults come from `defaults_*.yml`.
5. `optional: true` means the argument is omitted from the compose command entirely if it is not present in the metadata, rather than raising an error.
6. GRD fingerprint and location file references. Separated from general `inputs` because they are always routed to the `general-input-data` directory rather than the module-specific input directory.
7. Input files passed to the module. Each entry maps a logical argument name to a file path and a container mount point.
8. `transform: "filename"` extracts just the filename component from the full path before writing it to the compose command argument. The full path is used for the volume mount; only the filename is passed as the CLI argument to the container.
9. `external_volume: true` marks a file that comes from _another module's output_ rather than from input data on disk. The adapter mounts the upstream module's output directory rather than an input data directory.
10. Output files written by the module. These are declared so the adapter knows where to mount the output directory and what filenames to expect.
11. `output_type: "global"` — this output is a global sea-level projection (not spatially resolved). Used by `facts-total` to identify which outputs to aggregate across workflows.
12. `output_type: "local"` — this output is a spatially-resolved (local) sea-level projection.
13. Declares the Docker volume mounts. The three standard volumes are `module_specific_input`, `general_input`, and `output`. `host_path` values are dot-paths resolved from the experiment metadata at compose-generation time.
