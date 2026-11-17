"""Unit tests for application.generate_run_file, with a fake ExecutionBackend."""

from pathlib import Path

import pytest

from facts_experiment_builder.application import generate_run_file as module
from facts_experiment_builder.application.backend import RunInfo
from facts_experiment_builder.application.execution_graph import ExecutionGraph
from facts_experiment_builder.application.generate_run_file import generate_run_file
from facts_experiment_builder.core.experiment.loaded_config import (
    LoadedExperimentConfig,
)
from facts_experiment_builder.core.module.module_service_path_resolution import (
    APPTAINER_OUTPUT_KEY,
)
from tests.unit.helpers import make_config_raw, make_execution_plan

_EXPERIMENT_NAME = "experiments/exp"


class _FakeRepo:
    def __init__(self, raw: dict):
        self.raw = raw

    def get(self, config_path: Path) -> LoadedExperimentConfig:
        return LoadedExperimentConfig.from_dict(self.raw)


class _FakeBackend:
    """Records each call, in order."""

    output_key = APPTAINER_OUTPUT_KEY

    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def default_output_path(self, experiment_paths):
        return experiment_paths.experiment_dir / "run-file"

    def render(self, graph: ExecutionGraph, info: RunInfo) -> str:
        self.calls.append(("render", (graph, info)))
        return "content"

    def write(self, content: str, path: Path) -> None:
        self.calls.append(("write", (content, path)))


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / _EXPERIMENT_NAME).mkdir(parents=True)
    (tmp_path / _EXPERIMENT_NAME / "experiment-config.yaml").write_text("")
    return tmp_path


@pytest.fixture
def planned(monkeypatch):
    """Replace planning with a stub that records the data_paths it was given."""
    seen = {}

    class _Plan:
        workflows = {"wf1": None, "wf2": None}

    def fake_prepare(config, data_paths):
        seen["data_paths"] = data_paths
        return _Plan(), make_execution_plan()

    monkeypatch.setattr(module, "prepare_execution_plan", fake_prepare)
    return seen


def _run(workspace, backend, **kwargs):
    return generate_run_file(
        experiment_name=_EXPERIMENT_NAME,
        workspace_dir=workspace,
        experiment_repo=_FakeRepo(make_config_raw()),
        backend=backend,
        **kwargs,
    )


def test_writes_rendered_content_to_the_default_path(workspace, planned):
    backend = _FakeBackend()
    output = _run(workspace, backend)

    expected = workspace / _EXPERIMENT_NAME / "run-file"
    assert output.path == expected
    assert backend.calls[-1] == ("write", ("content", expected))
    assert [name for name, _ in backend.calls] == ["render", "write"]


def test_custom_output_path_wins_over_the_default(workspace, planned, tmp_path):
    backend = _FakeBackend()
    custom = tmp_path / "elsewhere" / "file"
    output = _run(workspace, backend, custom_output_path=custom)

    assert output.path == custom.resolve()
    assert backend.calls[-1] == ("write", ("content", custom.resolve()))


def test_planning_and_render_use_the_backends_output_location(workspace, planned):
    backend = _FakeBackend()
    _run(workspace, backend)

    expected = make_config_raw()[APPTAINER_OUTPUT_KEY]
    assert planned["data_paths"].output_data_location == expected
    _graph, info = dict(backend.calls)["render"]
    assert info.data_paths.output_data_location == expected
    assert info.workflow_names == ["wf1", "wf2"]
    assert info.workspace_dir == workspace
    assert info.config.nsamps == make_config_raw()["nsamps"]


def test_missing_experiment_dir_raises_file_not_found(tmp_path, planned):
    with pytest.raises(FileNotFoundError, match="experiment directory"):
        _run(tmp_path, _FakeBackend())


def test_missing_config_raises_file_not_found(tmp_path, planned):
    (tmp_path / _EXPERIMENT_NAME).mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="experiment-config.yaml"):
        _run(tmp_path, _FakeBackend())
