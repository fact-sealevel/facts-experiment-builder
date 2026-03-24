from click.testing import CliRunner
from facts_experiment_builder.cli.setup_new_experiment_cli import main as main_setup
from facts_experiment_builder.cli.generate_compose_cli import main as main_compose
from unittest.mock import patch


runner = CliRunner()


def test_setup_new_experiment_runs_successfully(
    project_root, monkeypatch, setup_args, experiment_name
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
            / "experiment-metadata.yml"
        ).exists()


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
