import pytest

from facts_experiment_builder.core.experiment.skeleton import (
    ExperimentSkeleton,
    parse_module_regions,
)


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


# totaling runs whenever sea-level modules are passed, including a single module (#146)
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
    with pytest.raises(ValueError, match="--supplied-totaled-sealevel-step-data"):
        ExperimentSkeleton.from_inputs(
            climate_step="fair-temperature",
            supplied_climate_step_data=None,
            sealevel_step="some-module",
            supplied_totaled_sealevel_step_data="data.nc",
            extremesealevel_step=None,
        )


@pytest.mark.parametrize(
    "climate_step,supplied",
    [
        (None, "data.nc"),  # supplied totaled sea-level data
        ("fair-temperature", None),  # no sea-level step at all
    ],
)
def test_experiment_skeleton_fails_if_esl_without_sealevel_modules(
    climate_step, supplied
):
    with pytest.raises(ValueError, match="--extremesealevel-step"):
        ExperimentSkeleton.from_inputs(
            climate_step=climate_step,
            supplied_climate_step_data=None,
            sealevel_step=None,
            supplied_totaled_sealevel_step_data=supplied,
            extremesealevel_step="extremesealevel-pointsoverthreshold",
        )
