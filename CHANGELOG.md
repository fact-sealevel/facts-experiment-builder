# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] 



## [0.6.0] - 2026-09-30 

### Added
- `ExperimentConfig` in `core.experiment` to hold config-building logic that was previously in the io layer ([PR #103](https://github.com/fact-sealevel/facts-experiment-builder/pull/103), [@e-marshall](https://github.com/e-marshall))
- `ExperimentRepository` port and adapter; `setup-experiment` and `generate-compose` now use its `.add()` / `.get()` methods to write and read experiment config files ([PR #109](https://github.com/fact-sealevel/facts-experiment-builder/pull/109), [@e-marshall](https://github.com/e-marshall))
- New `module_schemas` section in `experiment-config.yaml`, written by `setup-experiment`, that stores the schema of each module used in the experiment ([PR #115](https://github.com/fact-sealevel/facts-experiment-builder/pull/115), [@e-marshall](https://github.com/e-marshall))
- `WorkflowName` validation that fails fast on empty workflow names or names with invalid characters (ie. commas), which previously produced invalid docker compose service names ([PR #118](https://github.com/fact-sealevel/facts-experiment-builder/pull/118), [@e-marshall](https://github.com/e-marshall))
- Broader test coverage for `generate-compose` and writing compose files ([PR #119](https://github.com/fact-sealevel/facts-experiment-builder/pull/119), [@e-marshall](https://github.com/e-marshall))

### Changed
- Changed `--root` arg to `--workspace-dir` and removed use of `determine_root()` by `setup-experiment` and `generate-compose` commands ([PR #101](https://github.com/fact-sealevel/facts-experiment-builder/pull/101), [@e-marshall](https://github.com/e-marshall))
- Rename infra layer to io ([PR #101](https://github.com/fact-sealevel/facts-experiment-builder/pull/101), [@e-marshall](https://github.com/e-marshall))
- Removed `FileSystemExperimentStorage`; path-resolution logic moved to core so io only handles file system operations ([PR #102](https://github.com/fact-sealevel/facts-experiment-builder/pull/102), [@e-marshall](https://github.com/e-marshall))
- `ExperimentConfig` holds a `FactsExperiment` obj as an attr; all information needed by the experiment config template is now held in `ExperimentConfig`. Logic moved from `cli.generate_compose_cli` to `application.generate_compose`, and helpers from `application` moved to `core.experiment` / `core.module` ([PR #106](https://github.com/fact-sealevel/facts-experiment-builder/pull/106), [@e-marshall](https://github.com/e-marshall))
- Organized imports and renamed/moved modules: `core.experiment.facts_experiment` -> `core.experiment.experiment`, `core.experiment.experiment_skeleton` -> `core.experiment.skeleton`, `core.module.module_definition_source` -> `io.module_registry`, `plan.temperature_module_name` -> `plan.climate_module_name`; experiment plan moved out of `generate_compose` ([PR #108](https://github.com/fact-sealevel/facts-experiment-builder/pull/108), [@e-marshall](https://github.com/e-marshall))
- `ModuleRegistry` and `ExperimentRepository` protocols moved from `io.module_registry` / `io.experiment_repository` to a new `application.storage` module, so application needs define the ports rather than io ([PR #111](https://github.com/fact-sealevel/facts-experiment-builder/pull/111), [@brews](https://github.com/brews))
- Refactored `build_module_service_spec()` into smaller helpers. Module image must now be a string with a version tag (`url:tag`), and module outputs must be a dictionary ([PR #113](https://github.com/fact-sealevel/facts-experiment-builder/pull/113), [@e-marshall](https://github.com/e-marshall))
- **Breaking:** `generate-compose` no longer uses the module registry and the `--module-registry` arg is removed from it; module schemas are read from the experiment's `experiment-config.yaml` instead. `generate-compose` raises a `ValueError` for config files written before this change (without a `module_schemas` section); re-run `setup-experiment` to regenerate them ([PR #115](https://github.com/fact-sealevel/facts-experiment-builder/pull/115), [@e-marshall](https://github.com/e-marshall))
- Removed `cli/utils.py` (`configure_logging()` moved to `setup_experiment_cli.py`) and `io/workspace_loader.py` (`load_experiment_config()` moved to `io/experiment_repository.py`) ([PR #115](https://github.com/fact-sealevel/facts-experiment-builder/pull/115), [@e-marshall](https://github.com/e-marshall))
- Renamed `core/module/service_spec_utils.py` to `module_service_path_resolution.py` and moved the path-resolution functions from `module_service_spec.py` into it; renamed `check_data`'s `resolve_input_paths()` to `resolve_validate_input_paths()` so it no longer shares a name with the service-spec function; removed `core/source_resolver.py` ([PR #121](https://github.com/fact-sealevel/facts-experiment-builder/pull/121), [@e-marshall](https://github.com/e-marshall))
- `ModuleSchema.arguments` is now a validated `ArgumentsSpec` Pydantic model instead of a bare dict, and module yaml `source:` strings are parsed into a typed `SourcePath` when the yaml loads. `TopLevelParams` moved to `core.components.top_level_params` (still re-exported from `core.experiment.experiment`) and replaces `ModuleServiceSpecComponents.metadata` ([PR #122](https://github.com/fact-sealevel/facts-experiment-builder/pull/122), [@e-marshall](https://github.com/e-marshall))
- **breaking:** Module yaml validation is stricter: malformed `source:` strings, `metadata.<key>` sources that aren't a `TopLevelParams` field, a non-dict `arguments` section and a non-string `command` now raise at load time instead of resolving to `None` or `{}` when the compose file is generated. The unused `alternatives` arg-spec field is removed, so a module yaml that sets it fails validation ([PR #122](https://github.com/fact-sealevel/facts-experiment-builder/pull/122), [@e-marshall](https://github.com/e-marshall))
- The climate input of a sea-level module is now identified by its `climate_step_output` field instead of by the hard-coded names `climate-data-file` / `input-data-file`, so a module's CLI flag can have any name ([PR #122](https://github.com/fact-sealevel/facts-experiment-builder/pull/122), [@e-marshall](https://github.com/e-marshall))
- Simplified argument processing in `ModuleServiceSpec`: a single `_process_argument()` routes output and non-output args to their own container-path helpers (replacing `_process_output_argument()`), and CLI flags are built by one shared `_format_arg()` ([PR #122](https://github.com/fact-sealevel/facts-experiment-builder/pull/122), [@e-marshall](https://github.com/e-marshall))

### Fixed
- `generate-compose` failed for extreme sea-level modules other than `extremesealevel-pointsoverthreshold` (ie. `extremesealevel2-afs`) because a `gesla_dir` input was added to every module in that step; it is now only added if the module schema declares it. Missing input mounts now raise a clear `ValueError` ([PR #113](https://github.com/fact-sealevel/facts-experiment-builder/pull/113), [@e-marshall](https://github.com/e-marshall))
- Module field `default_value`s are now written as the field's `value` in `experiment-config.yaml` when no other value is provided ([PR #113](https://github.com/fact-sealevel/facts-experiment-builder/pull/113), [@e-marshall](https://github.com/e-marshall))
- `check-data` and module service specs had hardcoded output volume names and sometimes used a module yaml field's `source` instead of `name`; both now use `ModuleSchema` as the single source of truth for volume names ([PR #115](https://github.com/fact-sealevel/facts-experiment-builder/pull/115), [@e-marshall](https://github.com/e-marshall))
- List values for top-level params, fingerprint params, inputs without `multiple: true` and outputs were written into the compose command as a Python list string (ie. `--name=['a', 'b']`); they are now passed as one flag per item, as options already were ([PR #122](https://github.com/fact-sealevel/facts-experiment-builder/pull/122), [@e-marshall](https://github.com/e-marshall))

## [0.5.0] - 2026-07-20 

### Fixed
- Added two fields to module yamls of sea-level modules: 1) `pass_to_total`, true by default; set to false to prevent auxiliary outputs (such as `quantiles.nc`) from being passed to totaling step, 2) `climate_output_type`, used to specify which outptus from the climate step is expected by a sea-level module (ie.`gsat.nc` or `ohc.nc`) ([PR #83](https://github.com/fact-sealevel/facts-experiment-builder/pull/83),  [@e-marshall](https://github.com/e-marshall))
- Remove hard-coding of `"experiments/"` as parent directory of `--experiment-name`. A parent directory is not required but is recommended and should be included in `--experiment-name`. FEB resolves path based on `--root` and `--experiment-name` using `FileSystemExperimentStorage` obj ([PR #86](https://github.com/fact-sealevel/facts-experiment-builder/pull/86),  [@e-marshall](https://github.com/e-marshall))

### Added
- FEB recognizes and handles module schemas with entries in inputs section that are directories instead of files ([PR #82](https://github.com/fact-sealevel/facts-experiment-builder/pull/82),  [@e-marshall](https://github.com/e-marshall))
- Added Pydantic models for structure of individual entries in each section (top-level params, options, inputs, outputs,...) of a module yaml file ([PR #83](https://github.com/fact-sealevel/facts-experiment-builder/pull/83),  [@e-marshall](https://github.com/e-marshall))
- Add `module-registry` args to CLI commands that use registry and use `FileSystemModuleRegistry objs ([PR #86](https://github.com/fact-sealevel/facts-experiment-builder/pull/86),  [@e-marshall](https://github.com/e-marshall))
- Add `root` arg to CLI commands that write files (`setup-experiment`, `generate-compose`) to give option of specifying alternative working directory ([PR #86](https://github.com/fact-sealevel/facts-experiment-builder/pull/86),  [@e-marshall](https://github.com/e-marshall))


### Changed
- `feb generate-compose` fails loudly if service creation fails for individual module or workflow ([PR #82](https://github.com/fact-sealevel/facts-experiment-builder/pull/82), [@e-marshall](https://github.com/e-marshall))
- Small change to `InputArgSpec` to allow list of filenames to be passed in cases where multiple files may be passed for one input arg (ie. ssp-landwaterstorage). ([PR #85](https://github.com/fact-sealevel/facts-experiment-builder/pull/85),  [@e-marshall](https://github.com/e-marshall))
- Refactor module registry and how it is used in codebase ([PR #86](https://github.com/fact-sealevel/facts-experiment-builder/pull/86),  [@e-marshall](https://github.com/e-marshall))


## [0.4.1] - 2026-06-09 

### Fixed
- Bug related to `check-data` CLI command ([PR #77](https://github.com/fact-sealevel/facts-experiment-builder/pull/77), [@e-marshall](https://github.com/e-marshall))
- Added missing tlm-sterodynamics input data to setup guide instructions ([PR #78](https://github.com/fact-sealevel/facts-experiment-builder/pull/78),  [@e-marshall](https://github.com/e-marshall))

## [0.4.0] - 2026-06-09

### Added
- `feb init` command that initializes a facts workspace directory by creating a blank `experiments/` dir and cloning the module registry repo ([PR #72](https://github.com/fact-sealevel/facts-experiment-builder/pull/72), [@e-marshall](https://github.com/e-marshall))
- `feb check-data` command that checks to see which modules have input data downloaded at a provided location and if the contents match the expected structure and the files expected (as specified in the module registry) ([PR #72](https://github.com/fact-sealevel/facts-experiment-builder/pull/72), [@e-marshall](https://github.com/e-marshall)).
- Initial support for emulandice2. Still does not correctly handle all region options or write localized outputs ([PR #72](https://github.com/fact-sealevel/facts-experiment-builder/pull/72), [@e-marshall](https://github.com/e-marshall)).
- Expanded documentation surrounding experiments and downloading module input data ([PR #74](https://github.com/fact-sealevel/facts-experiment-builder/pull/74),  [@e-marshall](https://github.com/e-marshall)).
- New component of `feb init` that checks if there are more recent remote changes in the facts-module-registry repo that is cloned locally in the workspace, automatically creates .gitignore in workspace if not present and adds facts-module-registry to it ([PR #74](https://github.com/fact-sealevel/facts-experiment-builder/pull/74),  [@e-marshall](https://github.com/e-marshall)).

### Fixed
- Correct outputs now passed to totaling step ([PR #67](https://github.com/fact-sealevel/facts-experiment-builder/pull/67), [@e-marshall](https://github.com/e-marshall))

### Changed
- Changed quickstart guide name to setup guide in docs ([PR #75](https://github.com/fact-sealevel/facts-experiment-builder/pull/75), [@e-marshall](https://github.com/e-marshall))

## [0.3.1] - 2026-05-05

### Fixed
- Small typos in README ([7d984f7](7d984f72f740539850a4e42c8c6f683fbe647f5f), [@e-marshall](https://github.com/e-marshall))


## [0.3.0] - 2026-05-03

### Changed

- Move module registry to external repository; rename `setup-new-experiment` -> `setup-experiment` ([PR #60](https://github.com/fact-sealevel/facts-experiment-builder/pull/60), [@e-marshall](https://github.com/e-marshall))


## [0.2.0] - 2026-04-28

### Changed
- Containers associated with all modules in module registry now point to 'latest' tag, previously some pointed at specific versions ([PR 43](https://github.com/fact-sealevel/facts-experiment-builder/pull/43), [@e-marshall](https://github.com/e-marshall))
- Reformat CLI to `feb setup` and `feb generate` ([PR #44](https://github.com/fact-sealevel/facts-experiment-builder/pull/44), [@brews](https://github.com/brews))
- Rename `general-inputs` to `shared-in` and `experiment-metadata.yml` to `experiment-config.yml` ([PR #45](https://github.com/fact-sealevel/facts-experiment-builder/pull/45), [@e-marshall](https://github.com/e-marshall))
- Modules no longer have separate yaml files with default values, this information is now stored in the module yaml itself under `default_value` and `filename` keys. ([PR #55](https://github.com/fact-sealevel/facts-experiment-builder/pull/55), [@e-marshall](https://github.com/e-marshall))
- `setup-new-experiment` CLI command did have a `--framework-step` arg that accepted `'facts-total'` module. this was redundant and now removed. `'facts-total'` called if multiple sea-level modules are specified in experiment. ([PR #55](https://github.com/fact-sealevel/facts-experiment-builder/pull/55), [@e-marshall](https://github.com/e-marshall))
- Undo 43 ([PR #58](https://github.com/fact-sealevel/facts-experiment-builder/pull/58),[@e-marshall](https://github.com/e-marshall))
### Added
- Added option to automatically pass all modules instead of specifying them all in a workflow ([PR #48](https://github.com/fact-sealevel/facts-experiment-builder/commit/ee08b23759b8dec5141323c2886d634113c26f4e), [@e-marshall](https://github.com/e-marshall))

### Fixed
- Solved issues that prevented FEB from creating modules that include the [emulandice](https://github.com/fact-sealevel/emulandice) module ([PR #50](https://github.com/fact-sealevel/facts-experiment-builder/pull/50), [@e-marshall](https://github.com/e-marshall))
- Seed is no longer the same across all modules in an experiment. Instead of an experiment-level (`top-level`) argument passed in `setup-new-experiment` and spec. in `experiment-config.yml`, it is hard-coded in each module's ModuleRegistry yaml to match its value in Facts1 development branch ([PR #57](https://github.com/fact-sealevel/facts-experiment-builder/pull/57), [@e-marshall](https://github.com/e-marshall)).

## [0.1.0] - 2026-04-08

- Initial release

[Unreleased]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fact-sealevel/facts-experiment-builder/tag/v0.1.0
