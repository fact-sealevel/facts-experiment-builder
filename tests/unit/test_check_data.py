"""Unit tests for application/check_data.py."""

import yaml
from pathlib import Path

from facts_experiment_builder.application.check_data import (
    _check_module,
    _dir_to_module_names,
    check_module_data,
)
from facts_experiment_builder.core.registry.module_registry import ModuleRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_module_yaml(registry_dir: Path, module_name: str, inputs: list) -> None:
    """Write a minimal module YAML into a registry-style directory structure."""
    module_dir = registry_dir / module_name
    module_dir.mkdir(parents=True, exist_ok=True)
    snake = module_name.replace("-", "_")
    yaml_path = module_dir / f"{snake}_module.yaml"
    yaml_path.write_text(yaml.dump({"arguments": {"inputs": inputs}}))


def _write_module_yaml_with_args(
    registry_dir: Path, module_name: str, arguments: dict
) -> None:
    """Write a module YAML with an arbitrary arguments dict."""
    module_dir = registry_dir / module_name
    module_dir.mkdir(parents=True, exist_ok=True)
    snake = module_name.replace("-", "_")
    yaml_path = module_dir / f"{snake}_module.yaml"
    yaml_path.write_text(yaml.dump({"arguments": arguments}))


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
# _check_module — filename as a list (regression test for TypeError)
# ---------------------------------------------------------------------------


def test_check_module_filename_list_does_not_raise(tmp_path):
    """filename as a list should produce one InputFileCheck per entry, not raise TypeError."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml(
        registry_dir,
        "my-module",
        inputs=[
            {
                "name": "data-file",
                "filename": ["file_a.nc", "file_b.nc"],
                "mount": {"volume": "module_specific_in"},
            }
        ],
    )
    registry = ModuleRegistry(registry_dir)
    module_input_dir = tmp_path / "module_specific_input_data" / "my-module"
    module_input_dir.mkdir(parents=True)

    result = _check_module(
        module_name="my-module",
        module_input_dir=module_input_dir,
        registry=registry,
    )

    assert len(result.checks) == 2
    assert all(not c.skipped for c in result.checks)
    assert all(not c.exists for c in result.checks)  # files not created, so missing


def test_check_module_filename_list_detects_present_and_missing(tmp_path):
    """Each file in a filename list is checked independently."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml(
        registry_dir,
        "my-module",
        inputs=[
            {
                "name": "data-file",
                "filename": ["present.nc", "missing.nc"],
                "mount": {"volume": "module_specific_in"},
            }
        ],
    )
    registry = ModuleRegistry(registry_dir)
    module_input_dir = tmp_path / "module_specific_input_data" / "my-module"
    module_input_dir.mkdir(parents=True)
    (module_input_dir / "present.nc").touch()

    result = _check_module(
        module_name="my-module",
        module_input_dir=module_input_dir,
        registry=registry,
    )

    assert len(result.checks) == 2
    present = [c for c in result.checks if c.exists]
    missing = [c for c in result.checks if not c.exists and not c.skipped]
    assert len(present) == 1
    assert len(missing) == 1


# ---------------------------------------------------------------------------
# _check_module — other behaviours
# ---------------------------------------------------------------------------


def test_check_module_skips_output_volume(tmp_path):
    """Inputs with mount.volume == 'output' are skipped (inter-module dependencies)."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml(
        registry_dir,
        "my-module",
        inputs=[
            {
                "name": "climate-data-file",
                "filename": "climate.nc",
                "mount": {"volume": "output"},
            }
        ],
    )
    registry = ModuleRegistry(registry_dir)

    result = _check_module(
        module_name="my-module",
        module_input_dir=tmp_path / "module_data",
        registry=registry,
    )

    assert len(result.checks) == 1
    assert result.checks[0].skipped
    assert result.n_checkable == 0


def test_check_module_skips_missing_filename(tmp_path):
    """Inputs with no filename field are skipped."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml(
        registry_dir,
        "my-module",
        inputs=[{"name": "some-input", "mount": {"volume": "module_specific_in"}}],
    )
    registry = ModuleRegistry(registry_dir)

    result = _check_module(
        module_name="my-module",
        module_input_dir=tmp_path / "module_data",
        registry=registry,
    )

    assert result.checks[0].skipped


def test_check_module_string_filename_present(tmp_path):
    """A present file with a string filename is reported as exists=True."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml(
        registry_dir,
        "my-module",
        inputs=[
            {
                "name": "param-file",
                "filename": "params.nc",
                "mount": {"volume": "module_specific_in"},
            }
        ],
    )
    registry = ModuleRegistry(registry_dir)
    module_input_dir = tmp_path / "module_data"
    module_input_dir.mkdir()
    (module_input_dir / "params.nc").touch()

    result = _check_module(
        module_name="my-module",
        module_input_dir=module_input_dir,
        registry=registry,
    )

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


def test_check_module_fingerprint_params_module_specific_checked(tmp_path):
    """fingerprint_params with container_path /mnt/module_specific_in are checked."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml_with_args(
        registry_dir,
        "my-module",
        {
            "inputs": [],
            "fingerprint_params": [
                {
                    "name": "fp-data",
                    "filename": "fp_data.nc",
                    "mount": {"container_path": "/mnt/module_specific_in"},
                }
            ],
        },
    )
    registry = ModuleRegistry(registry_dir)
    module_input_dir = tmp_path / "module_data"
    module_input_dir.mkdir()

    result = _check_module(
        module_name="my-module",
        module_input_dir=module_input_dir,
        registry=registry,
    )

    assert len(result.checks) == 1
    assert not result.checks[0].skipped
    assert not result.checks[0].exists  # file not created


def test_check_module_fingerprint_params_module_specific_present(tmp_path):
    """A present fingerprint_params file in module-specific storage is detected."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml_with_args(
        registry_dir,
        "my-module",
        {
            "inputs": [],
            "fingerprint_params": [
                {
                    "name": "fp-data",
                    "filename": "fp_data.nc",
                    "mount": {"container_path": "/mnt/module_specific_in"},
                }
            ],
        },
    )
    registry = ModuleRegistry(registry_dir)
    module_input_dir = tmp_path / "module_data"
    module_input_dir.mkdir()
    (module_input_dir / "fp_data.nc").touch()

    result = _check_module(
        module_name="my-module",
        module_input_dir=module_input_dir,
        registry=registry,
    )

    assert result.n_present == 1
    assert result.n_missing == 0


def test_check_module_fingerprint_params_shared_not_checked_here(tmp_path):
    """fingerprint_params with /mnt/shared_in are NOT checked by _check_module."""
    registry_dir = tmp_path / "registry"
    _write_module_yaml_with_args(
        registry_dir,
        "my-module",
        {
            "inputs": [],
            "fingerprint_params": [
                {
                    "name": "fp-shared",
                    "filename": "grd_fingerprints.nc",
                    "mount": {"container_path": "/mnt/shared_in"},
                }
            ],
        },
    )
    registry = ModuleRegistry(registry_dir)

    result = _check_module(
        module_name="my-module",
        module_input_dir=tmp_path / "module_data",
        registry=registry,
    )

    assert result.checks == []
