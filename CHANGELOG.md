# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] 



## [0.2.0]

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

## [0.1.0]

- Initial release

[Unreleased]: https://github.com/fact-sealevel/facts-experiment-builder/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/fact-sealevel/facts-experiment-builder/tag/v0.2.0
[0.1.0]: https://github.com/fact-sealevel/facts-experiment-builder/tag/v0.1.0
