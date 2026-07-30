import tomllib
from pathlib import Path
from facts_experiment_builder.core.workspace.workspace import (
    WorkspaceConfig,
    FACTS2_WORKSPACE_FILENAME,
)


def load_workspace_file(workspace_dir: str) -> WorkspaceConfig:
    workspace_file_path = Path(workspace_dir, FACTS2_WORKSPACE_FILENAME)
    with open(workspace_file_path, "rb") as f:
        content = tomllib.load(f)

        config = WorkspaceConfig(**content)
        return config
