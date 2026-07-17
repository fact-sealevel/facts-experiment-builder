"""Unit tests for cli/check_data_cli.py."""

import pytest
import click
from click.testing import CliRunner
from facts_experiment_builder.cli.check_data_cli import (
    check_provided_paths,
    main,
)


def _write_module_registry(
    fake_registry, module_name="fair-temperature", filename="temp.nc"
):
    return fake_registry(
        {
            module_name: {
                "module_name": module_name,
                "container_image": "img:tag",
                "arguments": {
                    "inputs": [
                        {
                            "name": "temp-file",
                            "type": "file",
                            "source": "module_inputs.inputs.temp_file",
                            "filename": filename,
                            "mount": {
                                "container_path": "/mnt/module_specific_in",
                                "volume": "input",
                            },
                        }
                    ],
                    "fingerprint_params": [],
                    "options": [],
                    "outputs": {},
                },
                "volumes": {},
            }
        }
    )


def test_main_reports_all_present(tmp_path, fake_registry):
    registry_dir = _write_module_registry(fake_registry)

    module_dir = tmp_path / "data" / "module_specific_input_data" / "fair-temperature"
    module_dir.mkdir(parents=True)
    (module_dir / "temp.nc").touch()
    (tmp_path / "data" / "shared_input_data").mkdir(parents=True)

    result = CliRunner().invoke(
        main,
        [
            "--data-dir",
            str(tmp_path / "data"),
            "--module-registry",
            str(registry_dir),
        ],
    )

    assert result.exit_code == 0, (
        f"Output: \n{result.output} --- \nException: \n{result.exception} --- \n"
    )
    assert "All checked modules look good" in result.output
    assert "1/1 files present" in result.output


def test_main_reports_missing_file(tmp_path, fake_registry):
    registry_dir = _write_module_registry(fake_registry)

    module_dir = tmp_path / "data" / "module_specific_input_data" / "fair-temperature"
    module_dir.mkdir(parents=True)  # temp.nc deliberately not created
    (tmp_path / "data" / "shared_input_data").mkdir(parents=True)

    result = CliRunner().invoke(
        main,
        [
            "--data-dir",
            str(tmp_path / "data"),
            "--module-registry",
            str(registry_dir),
        ],
    )

    assert result.exit_code == 0
    assert "missing files" in result.output
    assert "missing:" in result.output
    assert "temp.nc" in result.output


def test_main_reports_unrecognized_dir(tmp_path, fake_registry):
    registry_dir = _write_module_registry(fake_registry)

    unrecognized = tmp_path / "data" / "module_specific_input_data" / "old-module"
    unrecognized.mkdir(parents=True)
    (tmp_path / "data" / "shared_input_data").mkdir(parents=True)

    result = CliRunner().invoke(
        main,
        [
            "--data-dir",
            str(tmp_path / "data"),
            "--module-registry",
            str(registry_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Unrecognized directories" in result.output
    assert "old-module" in result.output


def test_main_reports_no_module_data_found(tmp_path, fake_registry):
    registry_dir = _write_module_registry(fake_registry)

    (tmp_path / "data" / "module_specific_input_data").mkdir(parents=True)
    (tmp_path / "data" / "shared_input_data").mkdir(parents=True)

    result = CliRunner().invoke(
        main,
        [
            "--data-dir",
            str(tmp_path / "data"),
            "--module-registry",
            str(registry_dir),
        ],
    )

    assert result.exit_code == 0
    assert "No module data directories found" in result.output


# --- resolve_input_paths: data_dir-only cases ---


# def test_resolve_fails_when_both_subdirs_missing(tmp_path):
#     with pytest.raises(ValueError, match="Expected subdirectory not found:"):
#         resolve_input_paths(tmp_path, None, None)


# def test_resolve_fails_when_module_subdir_missing(tmp_path):
#     (tmp_path / "shared_input_data").mkdir()
#     with pytest.raises(
#         ValueError, match="Expected subdirectory not found:.*module_specific_input_data"
#     ):
#         resolve_input_paths(tmp_path, None, None)


# def test_resolve_fails_when_shared_subdir_missing(tmp_path):
#     (tmp_path / "module_specific_input_data").mkdir()
#     with pytest.raises(
#         ValueError, match="Expected subdirectory not found:.*shared_input_data"
#     ):
#         resolve_input_paths(tmp_path, None, None)


# def test_resolve_error_lists_existing_subdirs_when_misnamed(tmp_path):
#     (tmp_path / "incorrect_module_data_name").mkdir()
#     (tmp_path / "incorrect_shared_data_name").mkdir()

#     with pytest.raises(ValueError) as exc_info:
#         resolve_input_paths(tmp_path, None, None)

#     msg = str(exc_info.value)
#     assert "Expected subdirectory not found:" in msg
#     assert "incorrect_module_data_name" in msg
#     assert "incorrect_shared_data_name" in msg


# def test_resolve_data_dir_only_returns_derived_paths(tmp_path):
#     (tmp_path / "module_specific_input_data").mkdir()
#     (tmp_path / "shared_input_data").mkdir()

#     module_dir, shared_dir = resolve_input_paths(tmp_path, None, None)

#     assert module_dir == tmp_path / "module_specific_input_data"
#     assert shared_dir == tmp_path / "shared_input_data"


# # --- resolve_input_paths: explicit path cases ---


# def test_resolve_explicit_paths_returned_directly(tmp_path):
#     module_path = tmp_path / "my_modules"
#     shared_path = tmp_path / "my_shared"
#     module_path.mkdir()
#     shared_path.mkdir()

#     module_dir, shared_dir = resolve_input_paths(tmp_path, module_path, shared_path)

#     assert module_dir == module_path
#     assert shared_dir == shared_path


# def test_resolve_fails_when_explicit_module_path_missing(tmp_path):
#     shared_path = tmp_path / "shared"
#     shared_path.mkdir()

#     with pytest.raises(
#         ValueError, match="Module-specific input data directory not found"
#     ):
#         resolve_input_paths(tmp_path, tmp_path / "does_not_exist", shared_path)


# def test_resolve_fails_when_explicit_shared_path_missing(tmp_path):
#     module_path = tmp_path / "modules"
#     module_path.mkdir()

#     with pytest.raises(ValueError, match="Shared input data directory not found"):
#         resolve_input_paths(tmp_path, module_path, tmp_path / "does_not_exist")


# # --- resolve_input_paths: mixed (one explicit, one derived) ---


# def test_resolve_explicit_module_overrides_data_dir(tmp_path):
#     explicit_module = tmp_path / "custom_modules"
#     explicit_module.mkdir()
#     (tmp_path / "shared_input_data").mkdir()

#     module_dir, shared_dir = resolve_input_paths(tmp_path, explicit_module, None)

#     assert module_dir == explicit_module
#     assert shared_dir == tmp_path / "shared_input_data"


# def test_resolve_explicit_shared_overrides_data_dir(tmp_path):
#     (tmp_path / "module_specific_input_data").mkdir()
#     explicit_shared = tmp_path / "custom_shared"
#     explicit_shared.mkdir()

#     module_dir, shared_dir = resolve_input_paths(tmp_path, None, explicit_shared)

#     assert module_dir == tmp_path / "module_specific_input_data"
#     assert shared_dir == explicit_shared


# --- check_provided_paths: verifies ValueError is wrapped as click.UsageError ---


def test_check_provided_paths_wraps_as_usage_error(tmp_path):
    with pytest.raises(click.UsageError):
        check_provided_paths(tmp_path, None, None)
