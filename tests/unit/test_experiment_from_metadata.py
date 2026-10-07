"""Tests for FactsExperiment.from_metadata_dict() on a loaded experiment-config.yaml."""

from facts_experiment_builder.core.experiment.experiment import FactsExperiment


def _loaded_config() -> dict:
    """A config shaped like yaml.safe_load() of a template-written experiment-config."""
    return {
        "experiment_name": "experiments/my_experiment",
        "pipeline-id": "abc123",
        "scenario": "ssp585",
        "climate_module": "fair-temperature",
        "sealevel_modules": ["tlm-sterodynamics"],
        "framework_modules": ["facts-total"],
        "esl_modules": [],
        "projection_scale": "local",
        "workflows": {"wf1": "tlm-sterodynamics"},
        "module-specific-input-data": "/in/module",
        "shared-input-data": "/in/shared",
        "experiment-specific-input-data": [],
        "output-data-location": "/out",
        "fair-temperature": {"inputs": {}, "outputs": {}},
        "tlm-sterodynamics": {"inputs": {}, "outputs": {}},
        "facts-total": {"inputs": {}, "outputs": {}},
    }


def test_from_metadata_dict_reads_manifest_workflows_and_projection_scale():
    exp = FactsExperiment.from_metadata_dict(
        _loaded_config(), top_level_keys={"pipeline-id", "scenario"}
    )
    assert exp.experiment_name == "experiments/my_experiment"
    assert exp.climate_step.module_name == "fair-temperature"
    assert exp.sealevel_step.module_names == ["tlm-sterodynamics"]
    assert exp.projection_scale == "local"
    assert exp.workflows == {"wf1": "tlm-sterodynamics"}
    assert exp.top_level_params == {"pipeline-id": "abc123", "scenario": "ssp585"}


def test_from_metadata_dict_does_not_read_paths():
    """Experiment-level paths are resolved by resolve_experiment_data_paths(), not
    here."""
    exp = FactsExperiment.from_metadata_dict(_loaded_config(), top_level_keys=set())
    assert exp.paths == {}


def test_from_metadata_dict_path_keys_are_not_params_sections_or_extra():
    path_keys = {
        "module-specific-input-data",
        "shared-input-data",
        "experiment-specific-input-data",
        "output-data-location",
    }
    # top_level_keys=None exercises the fallback that infers top-level params
    exp = FactsExperiment.from_metadata_dict(_loaded_config(), top_level_keys=None)
    assert not path_keys & set(exp.top_level_params)
    assert not path_keys & set(exp.extra)
