import yaml

from facts_experiment_builder.core.experiment.experiment_config import (
    ConfigModuleSection,
    ExperimentConfig,
)
from facts_experiment_builder.io.write_config import (
    format_module_value,
    write_config_jinja2,
)
from facts_experiment_builder.core.experiment.experiment_config import (
    ConfigModuleSection,
    ExperimentConfig,
)

import yaml


def test_format_module_value_returns_correct_when_value_is_nested_dict():
    key = "rcmip_concentration_fname"
    value = {
        "clue": "clue about this input obj",
        "value": None,
        "filename": "/path/to/file",
    }
    indent = 2

    formatted = format_module_value(key=key, value=value, indent=indent)
    print(formatted)
    assert formatted == [
        "  rcmip_concentration_fname:",
        "    # clue about this input obj",
        '    "/path/to/file"  # filename from module defaults',
    ]


def test_write_config_writes_module_schemas_section(tmp_path):
    # create a small ExperimentConfig obj
    exp_config = ExperimentConfig(
        experiment_name="test_experiment",
        date_created="2026-09-22",
        projection_scale="local",
        manifest={},
        paths={},
        top_level_params={},
        module_sections={
            "fair-temperature": ConfigModuleSection(
                module_name="fair-temperature", values={}
            )
        },
        included_modules=[],
        inputs=[],
        workflows={},
        outputs=[],
        module_keys=["fair-temperature"],
        module_registry_version="0.1.0",
        module_schemas={
            "fair-temperature": {
                "module_name": "fair-temperature",
                "container_image": "xxxx",
            }
        },
    )
    write_config_jinja2(
        experiment_config=exp_config, config_path=tmp_path / "experiment-config.yaml"
    )
    # load yaml back in
    loaded = yaml.safe_load((tmp_path / "experiment-config.yaml").read_text())
    assert (
        loaded["module_schemas"]["fair-temperature"]["module_name"]
        == "fair-temperature"
    )
