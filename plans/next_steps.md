# Next steps

Follow-up work found during other changes. Line numbers refer to branch
`remove_ssplws_transform` on 2026-10-08 and may drift.

---

## Remove the dead `scenario_name` transform and `ScenarioConfig`

Found while removing the ssp-landwaterstorage scenario special case
(`remove_ssplws_transform`). Not ssp-landwaterstorage-specific, so left out of that
change.

**What is dead**
- The `scenario_name` branch in `ModuleServiceSpec._to_input_container_path()`
  (`core/module/module_service_spec.py` L311-315):
  ```python
  if transform == "scenario_name":
      if hasattr(value, "scenario_name"):
          value = value.scenario_name
      elif isinstance(value, dict):
          value = value.get("scenario_name", value.get("scenario", value))
  ```
- `ScenarioConfig` (`core/module/module_schema.py` L186-191), the only class with a
  `scenario_name` attribute. It is not used anywhere in `src/`, `tests/` or `docs/`.

**Why the branch never changes a value**
- In both registries (`../facts-module-registry`, `facts2-workspace/facts-module-registry`)
  9 arguments declare `transform: scenario_name`: the `scenario` top-level arg of
  bamber19-icesheets, deconto21-ais, fair-temperature, fair2-climate, fittedismip-gris,
  ipccar5-glaciers, ipccar5-icesheets, larmip-ais and tlm-sterodynamics. All read
  `source: metadata.scenario`.
- `metadata.scenario` resolves to `TopLevelParams.scenario: str | None`. For a string,
  `hasattr(value, "scenario_name")` and `isinstance(value, dict)` are both false, so
  the branch is a no-op.

**Change**
- Delete the `scenario_name` branch (the `filename` branch becomes the first `if`) and
  update the `_to_input_container_path()` docstring, which lists
  `(scenario_name, filename)`.
- Delete `ScenarioConfig`.
- Module YAMLs that still set `transform: scenario_name` keep loading: `transform` is a
  free-form `str | None` (`core/module/arg_specs.py` L40, L57, L100) and unknown values
  are ignored. Optionally remove `transform: "scenario_name"` from the registry YAMLs
  (separate repo).

**Verification**
- `tests/unit/test_scenario_passthrough.py` should keep passing (fair-temperature and
  tlm-sterodynamics there don't declare the transform; consider adding one that does).
- Generated compose for a real experiment (e.g. `v2_experiments/BC_my_facts_experiment`)
  is byte-identical before and after.

---

## Related registry cleanup (separate repo: facts-module-registry)

- The `ssp-landwaterstorage` module YAML still declares
  `transform: "scenario_name_ssp_landwaterstorage"` with help text "mapped from common
  name via scenario_name_mapping_ssp_landwaterstorage.yaml". FEB ignores both now.
- `../facts-module-registry/ssp-landwaterstorage/scenario_name_mapping_ssp_landwaterstorage.yaml`
  is no longer read. (It also defines the SSP keys twice; PyYAML kept the second set.)
