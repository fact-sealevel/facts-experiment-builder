"""Application logic for initializing a FACTS workspace.

Intended to be run once from a fresh project directory before any
`setup-experiment` or `generate-compose` work begins. Has no Click or
console imports — all output decisions belong to the CLI layer.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Optional
import subprocess

import yaml


REGISTRY_URL = "https://github.com/fact-sealevel/facts-module-registry.git"
REGISTRY_DIR_NAME = "facts-module-registry"
WORKSPACE_MARKER_FILENAME = ".facts-workspace"


class StepStatus(Enum):
    CREATED = auto()
    ALREADY_EXISTS = auto()
    FAILED = auto()


@dataclass
class InitStepResult:
    status: StepStatus
    message: str
    path: Optional[Path] = None


@dataclass
class WorkspaceInitResult:
    experiments_dir: InitStepResult
    registry: InitStepResult
    gitignore: InitStepResult
    marker_file: InitStepResult


def ensure_experiments_dir(workspace_dir: Path) -> InitStepResult:
    """Create experiments/ if absent.

    Returns CREATED or ALREADY_EXISTS.
    """
    experiments = workspace_dir / "experiments"
    if experiments.exists():
        return InitStepResult(StepStatus.ALREADY_EXISTS, "Already exists.", experiments)
    experiments.mkdir()
    return InitStepResult(StepStatus.CREATED, "Created.", experiments)


def ensure_registry_cloned(
    workspace_dir: Path,
    registry_url: str = REGISTRY_URL,
) -> InitStepResult:
    """Clone facts-module-registry if absent.

    Returns CREATED, ALREADY_EXISTS, or FAILED. Never raises — failure is encoded in the
    return value so the CLI layer decides how to handle it.
    """
    registry_dir = workspace_dir / REGISTRY_DIR_NAME
    if registry_dir.exists():
        return InitStepResult(
            StepStatus.ALREADY_EXISTS, "Already exists.", registry_dir
        )
    try:
        result = subprocess.run(
            ["git", "clone", registry_url, str(registry_dir)],
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError) as e:
        return InitStepResult(
            StepStatus.FAILED,
            f"Could not run git: {e}. Is git installed and on your PATH?",
            registry_dir,
        )
    if result.returncode != 0:
        return InitStepResult(
            StepStatus.FAILED,
            f"git clone failed: {result.stderr.strip()}",
            registry_dir,
        )
    return InitStepResult(StepStatus.CREATED, "Cloned.", registry_dir)


def ensure_gitignore(workspace_dir: Path) -> InitStepResult:
    """Add facts-module-registry/ to .gitignore, creating the file if needed.

    Prevents the cloned registry from being accidentally staged if the user later runs
    `git init` in their workspace.
    """
    gitignore_path = workspace_dir / ".gitignore"
    entry = f"{REGISTRY_DIR_NAME}/"

    if gitignore_path.exists():
        existing = gitignore_path.read_text()
        if entry in existing.splitlines():
            return InitStepResult(
                StepStatus.ALREADY_EXISTS, "Entry already present.", gitignore_path
            )
        separator = "" if existing.endswith("\n") else "\n"
        gitignore_path.write_text(existing + separator + entry + "\n")
        return InitStepResult(StepStatus.CREATED, "Entry added.", gitignore_path)

    gitignore_path.write_text(entry + "\n")
    return InitStepResult(StepStatus.CREATED, "Created.", gitignore_path)


def ensure_workspace_marker(
    workspace_dir: Path,
    registry_url: str = REGISTRY_URL,
) -> InitStepResult:
    """Write .facts-workspace YAML marker if absent.

    Never overwrites.
    """
    marker_path = workspace_dir / WORKSPACE_MARKER_FILENAME
    if marker_path.exists():
        return InitStepResult(StepStatus.ALREADY_EXISTS, "Already exists.", marker_path)
    contents = {
        "initialized_at": datetime.now(timezone.utc).isoformat(),
        "registry_url": registry_url,
    }
    marker_path.write_text(yaml.dump(contents, default_flow_style=False))
    return InitStepResult(StepStatus.CREATED, "Created.", marker_path)


def init_workspace(
    workspace_dir: Path,
    registry_url: str = REGISTRY_URL,
) -> WorkspaceInitResult:
    """Orchestrate all three init steps in dependency order.

    The marker is written last — it only exists when both prerequisites succeeded (or
    were already present). If the registry clone fails the marker step is skipped and
    returns FAILED.
    """
    experiments_result = ensure_experiments_dir(workspace_dir)
    registry_result = ensure_registry_cloned(workspace_dir, registry_url)
    gitignore_result = ensure_gitignore(workspace_dir)

    if registry_result.status == StepStatus.FAILED:
        marker_result = InitStepResult(
            StepStatus.FAILED,
            "Skipped: registry clone did not succeed.",
        )
    else:
        marker_result = ensure_workspace_marker(workspace_dir, registry_url)

    return WorkspaceInitResult(
        experiments_dir=experiments_result,
        registry=registry_result,
        gitignore=gitignore_result,
        marker_file=marker_result,
    )
