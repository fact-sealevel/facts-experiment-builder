# PR #137: Add apptainer command

## Summary

Adds a `generate-apptainer` command that turns an existing `experiment-config.yaml` into a bash script (`experiment-apptainer.sh`) which runs the experiment with Apptainer instead of Docker Compose. It also includes two fixes merged into this branch: single-module ESL experiments (#148), and removal of the now-unreachable standalone ESL path (#149).

### New: `generate-apptainer`
- **CLI** (`cli/generate_apptainer_cli.py`):
  - available as `generate-apptainer` and `feb generate-apptainer`
  - options: `--experiment-name`, `--workspace-dir`, `--custom-script-path`, `--debug`
- **Application** (`application/generate_apptainer.py`): reuses the compose pipeline up to the format-agnostic `_ExecutionPlan`, then groups services into four stages:
  1. the climate module, plus sea-level modules that don't use climate output
  2. sea-level modules that use climate output, gated on the climate output files
  3. facts-total, one job per workflow × output type, run in parallel in the background and then waited on
  4. ESL, one service per workflow, run in sequence after Stage 3
- **Script rendering** (`io/write_apptainer.py`, `templates/apptainer_experiment.sh.j2`): a Jinja2 template with `StrictUndefined`. The generated script:
  - pulls each image once into a versioned SIF (`<service>-<tag>.sif`) under `<workspace>/apptainer_experiments/sif/`
  - creates every service output directory
  - runs each service with `apptainer run --no-home --containall --pwd /`, plus per-service `--bind` and `--env` flags
  - fails fast (`set -euo pipefail`, PID checks for background jobs, a 30-minute timeout on output polling)
  - is written with execute permission
- **Service spec** (`core/module/apptainer_service_spec.py`): new `ApptainerServiceSpec`, produced by `ModuleServiceSpec.generate_apptainer_service()`. It carries binds, args, env, image reference, wait files and the host output paths.
- **Output location:** Apptainer outputs go to `<experiment_dir>/output-apptainer/` (`ExperimentPaths.apptainer_output_dir`) instead of the config's `output-data-location`, so Compose and Apptainer runs of the same experiment don't overwrite each other.
- **`command: main` handling:** the subcommand is now omitted when building command args (`_build_command_args`), instead of being stripped afterwards in the compose renderer. Both Compose and Apptainer get the same args.
- **Docs:** new `docs/generate_apptainer.md` covering prerequisites, workspace and data setup, the resulting layout, and running the script.

### Fixes merged into this branch
- **#148, single sea-level module + ESL:** facts-total now runs for every experiment with sea-level modules, and a single module gets the `all-modules` workflow automatically. An ESL step now requires sea-level modules. Generating now raises for configs with a totaling step but no workflows (**breaking** for single-module experiments set up with earlier versions, which need a `workflows` entry or to be set up again).
- **#149:** removes `_ExecutionPlan.standalone_esl_specs` and the standalone ESL services from both renderers, since ESL now always runs per workflow.

### Tests
- New: `test_generate_apptainer.py`, `test_write_apptainer.py`, `test_generate_apptainer_cli.py`, plus `generate_apptainer_service` / `host_output_paths` cases in `test_module_service_spec.py`.
- From #148/#149: `test_workflow_prompts.py`, `test_experiment_plan.py`, `test_experiment_skeleton.py`, `test_execution_plan.py`, `test_generate_compose_property.py`.
- Full unit suite: 523 passed.

---

## Review notes (not for the PR description)

Ordered by how much each one matters. Based on reading the full diff against `main` (28 files) and running the unit suite; a generated script has not been run under Apptainer.

1. **README example is broken.** The `setup-experiment` example now has comments after the line-continuation backslashes, e.g. `--module-specific-input-data /path/to/module/inputs \ #replace this with…`. A backslash followed by a space no longer continues the line, so bash ends the command there and tries to run the next line as its own command (confirmed with a small bash test: `--y: command not found`). Put the comments on their own lines above the command, or in the text after it.
2. **No changelog entry for the main feature.** `CHANGELOG.md` has entries for #148 and #149, but nothing under Added for `generate-apptainer` itself, or for the new `output-apptainer/` location and `docs/generate_apptainer.md`.
3. **The docs still describe the command as branch-only.** `docs/generate_apptainer.md` says `generate-apptainer` is only on `add_apptainer_command`, and every `uvx` example uses `@add_apptainer_command`. Once this merges, those should point to `main`.
4. **The same image may be pulled many times.** SIF files are named `<service_name>-<tag>`, and per-workflow services use their service name as `module_name` (e.g. `facts-total-wf1-global`). So every facts-total job and every ESL service pulls its own copy of the same image: two workflows mean four facts-total pulls and two ESL pulls. Modules that share an image (`ipccar5-glaciers` and `ipccar5-icesheets`) also get separate SIFs. This wastes time and disk space but doesn't produce wrong results. Naming SIFs by `image_name-tag` would fix it.
5. **Smaller points:**
   - **Stage 3 binds:** all facts-total jobs use the `BINDS` from `stage3[0]`. That's fine while every facts-total service has the same binds, but nothing checks it.
   - **Services with no arguments:** the template uses `spec.args[-1]`, which would fail to render for a service with no arguments. Unlikely in practice.
   - **`--debug` does nothing:** it sets the logger to `INFO`, which is already the default. It matches `generate-compose`, so it may be intentional.
   - **SIF location is fixed:** `apptainer_experiments/sif` is always under the workspace, wherever the experiment lives. The docs describe this, so it's a convention rather than a bug, but it's worth knowing for the "no hardcoded paths" checklist item.
   - **Global tool install:** `~/.local/bin` won't get the `generate-apptainer` entry point until this is on `main` and the tool is reinstalled.
