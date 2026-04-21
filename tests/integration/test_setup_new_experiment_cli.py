from click.testing import CliRunner
from facts_experiment_builder.cli.setup_new_experiment_cli import main as main_setup
from facts_experiment_builder.cli.generate_compose_cli import main as main_compose
from facts_experiment_builder.core.experiment import FactsExperiment
from unittest.mock import patch
import yaml

runner = CliRunner()


def test_setup_new_experiment_runs_successfully(
    project_root,
    monkeypatch,
    setup_args,
    experiment_name,
    scenario,
    nsamps,
    pyear_start,
    pyear_end,
    pyear_step,
    baseyear,
    pipeline_id,
    seed,
):
    monkeypatch.chdir(project_root)
    with patch(
        "facts_experiment_builder.cli.setup_new_experiment_cli._collect_workflows",
        return_value={"wf1": "bamber19-icesheets,deconto21-ais,fittedismip-gris"},
    ):
        result = runner.invoke(main_setup, setup_args, catch_exceptions=False)

        assert result.exit_code == 0, result.output
        assert (
            project_root
            / "experiments"
            / str(experiment_name)
            / "experiment-config.yaml"
        ).exists()

        # roundtrip
        # build metadata path using fixtures in conftest
        metadata_path = (
            project_root
            / "experiments"
            / str(experiment_name)
            / "experiment-config.yaml"
        )
        # read metadata file
        metadata_dict = yaml.safe_load(metadata_path.read_text())
        # create experiment
        experiment = FactsExperiment.from_metadata_dict(metadata_dict)
        # now assert that the FactsExperiment object is how we expect it to be
        assert experiment.experiment_name == experiment_name, (
            f"Expected {experiment_name}, received {experiment.experiment_name}"
        )
        assert experiment.top_level_params == {
            "scenario": scenario,
            "pyear_start": pyear_start,
            "pyear_end": pyear_end,
            "pyear_step": pyear_step,
            "baseyear": baseyear,
            "nsamps": nsamps,
            "pipeline-id": pipeline_id,
            "seed": seed,
            "location-file": "location.lst",
        }
        experiment_steps = experiment.list_all_steps()
        all_module_names = [
            spec.module_name
            for step in experiment_steps
            for spec in step.module_specs()
        ]
        assert "fair-temperature" in all_module_names
        assert "bamber19-icesheets" in all_module_names
        assert "facts-total" in all_module_names
        assert "extremesealevel-pointsoverthreshold" in all_module_names


def test_generate_compose_runs_successfully(
    project_root, monkeypatch, setup_args, compose_args, experiment_name
):
    monkeypatch.chdir(project_root)
    with patch(
        "facts_experiment_builder.cli.setup_new_experiment_cli._collect_workflows",
        return_value={"wf1": "bamber19-icesheets,deconto21-ais,fittedismip-gris"},
    ):
        runner.invoke(main_setup, setup_args, catch_exceptions=False)

        result = runner.invoke(main_compose, compose_args, catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert (
        project_root / "experiments" / str(experiment_name) / "experiment-compose.yaml"
    ).exists()


def test_setup_new_experiment_fails_if_experiment_already_exists(
    project_root, monkeypatch, setup_args
):
    monkeypatch.chdir(project_root)
    with patch(
        "facts_experiment_builder.cli.setup_new_experiment_cli._collect_workflows",
        return_value={"wf1": "bamber19-icesheets,deconto21-ais,fittedismip-gris"},
    ):
        runner.invoke(main_setup, setup_args)
        result = runner.invoke(main_setup, setup_args)
    assert result.exit_code != 0


def test_generate_compose_fails_if_metadata_file_missing(
    project_root, monkeypatch, compose_args
):
    monkeypatch.chdir(project_root)
    result = runner.invoke(main_compose, compose_args)
    assert result.exit_code != 0
