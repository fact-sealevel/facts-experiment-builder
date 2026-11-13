# `generate-apptainer` user guide

`feb generate-apptainer` reads an experiment's `experiment-config.yaml` and writes `experiment-apptainer.sh`, a bash script that runs the experiment with [Apptainer](https://apptainer.org/) instead of Docker Compose. It is the Apptainer equivalent of `feb generate-compose`, for systems where Docker isn't available, such as HPC clusters.

The examples use `feb`. If you run FEB with `uvx` instead of installing it, replace `feb` with `uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main feb` (see [Installation](../README.md#installation)).

---

## Before you start

You need:

- **Apptainer**, on the machine where you will run the script. FEB itself doesn't need Apptainer; you can generate the script on one machine and run it on another (see [Generating and running on different machines](#generating-and-running-on-different-machines)).
- **A workspace with input data**, set up as for `generate-compose`: `feb init`, the input data downloads, and `feb check-data`. The [Setup guide](SETUP.md) walks through these steps.
- **An experiment created with `feb setup-experiment`.** `generate-apptainer` uses the same `experiment-config.yaml` as `generate-compose`; there are no Apptainer-specific setup options.

### Experiments created with older versions of FEB

`generate-apptainer` writes module outputs to the `apptainer-output-data-location` set in `experiment-config.yaml`. `setup-experiment` writes this key, but experiments set up with older versions don't have it, and `generate-apptainer` fails with:

```
experiment-config.yaml has no 'apptainer-output-data-location' value. ...
```

Add the key to `experiment-config.yaml` by hand, or set the experiment up again. A good default is the `output-apptainer` subdirectory of the experiment directory:

```yaml
apptainer-output-data-location: "/abs/path/to/workspace/experiments/my_first_experiment/output-apptainer"
```

---

## Generate the script

From the workspace directory:

```shell
feb generate-apptainer --experiment-name experiments/my_first_experiment
```

`--experiment-name` is the experiment directory, relative to `--workspace-dir`: the same value you passed to `setup-experiment`.

| Option | Required | Default | Description |
|---|---|---|---|
| `--experiment-name` | yes | — | Experiment directory, relative to the workspace, e.g. `experiments/my_first_experiment` |
| `--workspace-dir` | no | current directory | Workspace directory |
| `--custom-script-path` | no | `<experiment dir>/experiment-apptainer.sh` | Where to write the script instead |
| `--debug` | no | off | More detailed logging |

`generate-apptainer` checks `experiment-config.yaml` before writing anything. It fails with a message if a required value (`experiment_name`, `pipeline-id`, `nsamps`, `scenario`, `baseyear`, `pyear_start`, `pyear_end`, `pyear_step`, `module-specific-input-data`, `shared-input-data`) is missing, or if `nsamps`, `baseyear` or a `pyear_*` value isn't an integer.

### What it creates

```
workspace/
├── apptainer_sif_files/              ← Apptainer images, pulled by the script when it runs
└── experiments/
    └── my_first_experiment/
        ├── experiment-config.yaml    ← from setup-experiment
        ├── experiment-apptainer.sh   ← written by generate-apptainer
        └── output-apptainer/         ← apptainer-output-data-location (default)
            ├── <one directory per module>
            └── facts-total/
```

- **`experiment-apptainer.sh`** is made executable.
- **The output directories** are created when you generate the script, under `apptainer-output-data-location`: one per module, and one `facts-total/` shared by all facts-total services. The script also creates them (`mkdir -p`) when it runs.
- **`apptainer_sif_files/`** is always in the workspace directory, wherever the experiment is, so all experiments in a workspace share it. The script creates it.

Docker Compose runs write to `compose-output-data-location` (by default `output-compose/`), so you can run the same experiment with both and the outputs won't overwrite each other.

---

## Run the script

```shell
bash experiments/my_first_experiment/experiment-apptainer.sh
```

**Run it with `bash`, not `sh`.** The script uses bash features. Where `sh` is a different shell (e.g. `dash` on Ubuntu and Debian), `sh experiment-apptainer.sh` fails straight away with `set: Illegal option -o pipefail`.

The script uses `set -euo pipefail`, so it stops at the first error.

### What the script does

1. **Sets variables** for paths and experiment parameters, from `experiment-config.yaml` at the time you generated the script.
2. **Creates output directories** and `apptainer_sif_files/`.
3. **Pulls images.** Each module image is pulled from its full reference in the module's YAML (e.g. `ghcr.io/fact-sealevel/fair-temperature:0.2.1`) and saved as `<service>-<image tag>.sif`, e.g. `fair-temperature-0.2.1.sif`. An image that is already in `apptainer_sif_files/` isn't pulled again, so experiments in the same workspace that use the same image version share one copy.
4. **Runs the modules in four stages:**

   | Stage | Services | How they run |
   |---|---|---|
   | 1 | The climate module, and sea-level modules that don't use climate output | One after another |
   | 2 | Sea-level modules that use climate output | One after another, after the climate output files they read exist. The script checks every 5 seconds and fails after 30 minutes. |
   | 3 | facts-total: one per workflow and output type (`global`, and `local` for local projections) | In parallel; the script waits for all of them and fails if any fail |
   | 4 | Extreme sea-level modules: one per extreme sea-level module and workflow | One after another |

Each module gets the same command-line arguments as in `experiment-compose.yaml`. Inputs that a module's YAML declares with `envvar` are passed as environment variables (`--env`), as Compose passes them under `environment:`.

Containers run with `--containall --no-home`, so your home directory isn't available inside them, and start in `/` (`--pwd /`). All module paths are absolute paths in the container, so the working directory doesn't affect results.

---

## Generating and running on different machines

Paths in the script are absolute paths on the machine where you ran `generate-apptainer`. To run the script somewhere else, such as a VM that has Apptainer (e.g. Lima on macOS):

1. Keep the workspace at a path that the other machine mounts at the **same** location, with write access.
2. Run `generate-apptainer` on the first machine. This creates the output directories.
3. On the other machine, run the script with `bash`. For a VM, start a new VM session first, so the new output directories show up in the mount.

---

## Notes

- **Regenerate after changes.** Paths, parameters and image versions are fixed in the script when it is generated. If you move the workspace, edit `experiment-config.yaml`, or change a module's image tag, run `generate-apptainer` again.
- **Old images stay in `apptainer_sif_files/`.** After an image tag changes, the script pulls the new version under a new file name. The old `.sif` file isn't removed; delete it by hand if you don't need it.
- **To use your own copies of images,** put them in `apptainer_sif_files/` with the file names the script expects (`<service>-<image tag>.sif`) before running it. Files named without the tag (e.g. `fair-temperature.sif`) aren't used.
- **Generating the script doesn't change `experiment-config.yaml`,** so you can regenerate it at any time.
