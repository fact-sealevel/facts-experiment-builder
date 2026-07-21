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
    assert "1/1 expected entries present" in result.output


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


def test_check_provided_paths_wraps_as_usage_error(tmp_path):
    with pytest.raises(click.UsageError):
        check_provided_paths(tmp_path, None, None)
