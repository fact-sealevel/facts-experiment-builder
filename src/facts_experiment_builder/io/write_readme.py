"""Write an experiment's README.md, recording how setup-experiment created it."""

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined

logger = logging.getLogger(__name__)

_TEMPLATE_NAME = "experiment-readme.md.j2"


def write_experiment_readme(
    readme_path: Path,
    experiment_name: str,
    experiment_location: Path,
    date_created: datetime,
    command_name: str,
    setup_command: str,
    feb_version: str,
    workflows: dict[str, str | list[str]],
) -> bool:
    """Render the experiment README to `readme_path`.

    Never overwrites: if `readme_path` already exists (the experiment directory may
    have existed before setup), nothing is written and False is returned. Returns
    True when the README was written.

    `workflows` maps workflow name to its modules, either a comma-separated string or
    a list of module names.
    """
    if readme_path.exists():
        logger.warning("Not writing %s: file already exists.", readme_path)
        return False

    env = Environment(
        loader=PackageLoader("facts_experiment_builder", "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    rendered = env.get_template(_TEMPLATE_NAME).render(
        experiment_name=experiment_name,
        experiment_location=experiment_location,
        date_created=date_created,
        command_name=command_name,
        setup_command=setup_command,
        feb_version=feb_version,
        workflows={
            name: modules if isinstance(modules, str) else ", ".join(modules)
            for name, modules in workflows.items()
        },
    )
    readme_path.write_text(rendered)
    return True
