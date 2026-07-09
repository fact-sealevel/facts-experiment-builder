from facts_experiment_builder.core.experiment.experiment_skeleton import (
    parse_module_regions,
    ExperimentSkeleton,
)
import pytest


def test_parse_module_regions_fails_if_no_regions_specified():
    entries = [("module-name=",), ("module-name",)]
    for entry in entries:
        with pytest.raises(ValueError):
            parse_module_regions(entry)


def test_one_module_multiple_regions_succeeds():
    example_in = ("module-name=RGI01,RGI02,RGI03",)
    expected_out = {"module-name": ["RGI01", "RGI02", "RGI03"]}
    result = parse_module_regions(example_in)
    assert result == expected_out


def test_one_module_one_region_succeeds():
    example_in = ("module-name=RGI01",)
    expected_out = {"module-name": ["RGI01"]}
    result = parse_module_regions(example_in)
    assert result == expected_out


def test_parse_module_regions_fails_if_missing_equals():
    example_in = ("modulename:RGI01,RGI02",)
    with pytest.raises(ValueError):
        parse_module_regions(example_in)


# this is testing the scenarios covered in lines 92-100 in experiment skeleton
@pytest.mark.parametrize(
    "supplied,modules,expected",
    [
        ("data.nc", None, None),
        (None, None, None),
        (None, "a", "facts-total"),
        (None, "a,b", "facts-total"),
    ],
)
def test_totaling_rules(supplied, modules, expected):
    skeleton = ExperimentSkeleton.from_inputs(
        climate_step="fair-temperature" if not supplied else None,
        supplied_climate_step_data=None,
        sealevel_step=modules,
        supplied_totaled_sealevel_step_data=supplied,
        extremesealevel_step=None,
    )
    assert skeleton.totaling_module == expected


def test_experiment_skeleton_fails_if_climate_data_and_module_passed():
    with pytest.raises(ValueError):
        ExperimentSkeleton.from_inputs(
            climate_step="fair-temperature",
            supplied_climate_step_data="data.nc",
            sealevel_step="some-module",
            supplied_totaled_sealevel_step_data=None,
            extremesealevel_step=None,
        )


def test_experiment_skeleton_fails_if_sealevel_data_and_module_passed():
    with pytest.raises(ValueError):
        ExperimentSkeleton.from_inputs(
            climate_step="fair-temperature",
            supplied_climate_step_data="data.nc",
            sealevel_step="some-module",
            supplied_totaled_sealevel_step_data=None,
            extremesealevel_step=None,
        )
