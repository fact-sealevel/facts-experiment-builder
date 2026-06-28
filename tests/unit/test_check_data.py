"""Unit tests for application/check_data.py."""

from facts_experiment_builder.application.check_data import (
    _check_module,
    _dir_to_module_names,
    check_module_data,
    ModuleCheckResult,
)
from facts_experiment_builder.core.registry.module_registry import ModuleRegistry
from facts_experiment_builder.core.module.module_schema import ModuleSchema


# ---------------------------------------------------------------------------
# _dir_to_module_names
# ---------------------------------------------------------------------------


def test_dir_to_module_names_exact_match():
    known = frozenset(["fair-temperature", "bamber19-icesheets"])
    assert _dir_to_module_names("fair-temperature", known) == ["fair-temperature"]


def test_dir_to_module_names_shared_prefix():
    known = frozenset(["ipccar5-glaciers", "ipccar5-icesheets", "fair-temperature"])
    result = _dir_to_module_names("ipccar5", known)
    assert sorted(result) == ["ipccar5-glaciers", "ipccar5-icesheets"]


def test_dir_to_module_names_unrecognized():
    known = frozenset(["fair-temperature"])
    assert _dir_to_module_names("old-module", known) == []


# ---------------------------------------------------------------------------
# _check_module — other behaviours
# ---------------------------------------------------------------------------


def test_check_module_skips_output_volume(
    tmp_path,
    climate_data_file_arg_spec,
):
    """Inputs with mount.volume == 'output' are skipped (inter-module dependencies)."""
    schema = ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={"inputs": [climate_data_file_arg_spec.model_dump()], "outputs": {}},
        volumes={},
    )
    result = ModuleCheckResult(module_name="my-module")
    result = _check_module(result, schema, tmp_path / "module_data")

    assert len(result.checks) == 1
    assert result.checks[0].skipped
    assert result.n_checkable == 0


def test_check_module_skips_missing_filename(tmp_path, non_file_input_arg_spec):
    """Dir inputs with no default_value are skipped (no checkable path)."""
    schema = ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={"inputs": [non_file_input_arg_spec.model_dump()], "outputs": {}},
        volumes={},
    )
    result = ModuleCheckResult(module_name="my-module")
    result = _check_module(result, schema, tmp_path / "module_data")

    assert result.checks[0].skipped


def test_check_module_string_filename_present(
    tmp_path, random_module_specific_inputs_arg_spec
):
    """A present file with a string filename is reported as exists=True."""
    module_input_dir = tmp_path / "module_data"
    module_input_dir.mkdir()
    (module_input_dir / "random_file_name.nc").touch()
    schema = ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={
            "inputs": [random_module_specific_inputs_arg_spec.model_dump()],
            "outputs": {},
        },
        volumes={},
    )
    result = ModuleCheckResult(module_name="my-module")
    result = _check_module(result, schema, module_input_dir)

    assert result.n_present == 1
    assert result.n_missing == 0


# ---------------------------------------------------------------------------
# check_module_data — integration
# ---------------------------------------------------------------------------


def test_check_module_data_unrecognized_dir(tmp_path):
    """Directories that don't match any registry module are reported as unrecognized."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    registry = ModuleRegistry(registry_dir)

    module_specific = tmp_path / "module_specific_input_data"
    (module_specific / "unknown-module").mkdir(parents=True)

    result = check_module_data(
        module_specific_input_dir=module_specific,
        shared_input_dir=tmp_path / "shared",
        registry=registry,
    )

    assert result.unrecognized_dirs == ["unknown-module"]
    assert result.module_results == []


def test_check_module_data_empty_dir(tmp_path):
    """An empty module_specific_input_data dir returns an empty result."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    registry = ModuleRegistry(registry_dir)

    module_specific = tmp_path / "module_specific_input_data"
    module_specific.mkdir()

    result = check_module_data(
        module_specific_input_dir=module_specific,
        shared_input_dir=tmp_path / "shared",
        registry=registry,
    )

    assert result.module_results == []
    assert result.unrecognized_dirs == []


def test_check_module_data_missing_dir(tmp_path):
    """A non-existent module_specific_input_data dir returns an empty result without error."""
    registry = ModuleRegistry(tmp_path / "registry")

    result = check_module_data(
        module_specific_input_dir=tmp_path / "does_not_exist",
        shared_input_dir=tmp_path / "shared",
        registry=registry,
    )

    assert result.module_results == []


# ---------------------------------------------------------------------------
# _check_module — fingerprint_params with module-specific storage
# ---------------------------------------------------------------------------


def test_check_module_fingerprint_params_module_specific_checked(
    tmp_path, fp_module_specific_arg_spec
):
    """fingerprint_params with container_path /mnt/module_specific_in are checked."""
    schema = ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={
            "inputs": [],
            "fingerprint_params": [fp_module_specific_arg_spec.model_dump()],
            "outputs": {},
        },
        volumes={},
    )
    module_input_dir = tmp_path / "module_data"
    module_input_dir.mkdir()
    result = ModuleCheckResult(module_name="my-module")
    result = _check_module(result, schema, module_input_dir)

    assert len(result.checks) == 1
    assert not result.checks[0].skipped
    assert not result.checks[0].exists


def test_check_module_fingerprint_params_module_specific_present(
    tmp_path, fp_module_specific_arg_spec
):
    """A present fingerprint_params file in module-specific storage is detected."""
    module_input_dir = tmp_path / "module_data"
    module_input_dir.mkdir()
    (module_input_dir / "fp_data.nc").touch()
    schema = ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={
            "inputs": [],
            "fingerprint_params": [fp_module_specific_arg_spec.model_dump()],
            "outputs": {},
        },
        volumes={},
    )
    result = ModuleCheckResult(module_name="my-module")
    result = _check_module(result, schema, module_input_dir)

    assert result.n_present == 1
    assert result.n_missing == 0


def test_check_module_fingerprint_params_shared_not_checked_here(
    tmp_path, fp_shared_arg_spec
):
    """fingerprint_params with /mnt/shared_in are NOT checked by _check_module."""
    schema = ModuleSchema(
        module_name="my-module",
        container_image="img:tag",
        arguments={
            "inputs": [],
            "fingerprint_params": [fp_shared_arg_spec.model_dump()],
            "outputs": {},
        },
        volumes={},
    )
    result = ModuleCheckResult(module_name="my-module")
    result = _check_module(result, schema, tmp_path / "module_data")

    assert result.checks == []
