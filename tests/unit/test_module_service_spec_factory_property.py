"""Property tests for build_module_service_spec()."""

from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from facts_experiment_builder.application.module_service_spec_factory import (
    build_module_service_spec,
)
from facts_experiment_builder.core.module.arg_specs import ArgumentsSpec
from facts_experiment_builder.core.module.module_schema import ModuleSchema
from facts_experiment_builder.core.module.module_service_path_resolution import (
    resolve_experiment_data_paths,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_module_name = st.from_regex(r"[a-z][a-z0-9]{2,8}", fullmatch=True)
_image_url = st.from_regex(r"[a-z]+/[a-z]+", fullmatch=True)
_image_tag = st.from_regex(r"[a-z0-9]+", fullmatch=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema(name: str) -> ModuleSchema:
    return ModuleSchema(
        module_name=name,
        container_image="img:tag",
        arguments=ArgumentsSpec(),
        volumes={},
    )


def _metadata(module_name: str, image: str = "repo/img:latest") -> dict:
    return {
        "shared-input-data": "/in/shared",
        "module-specific-input-data": "/in/module",
        "output-data-location": "/out",
        module_name: {"inputs": {}, "outputs": {}, "image": image},
    }


def _build(module_name: str, image: str = "repo/img:latest") -> tuple:
    schema = _schema(module_name)
    metadata = _metadata(module_name, image=image)
    with patch(
        "facts_experiment_builder.application.module_service_spec_factory.ensure_module_output_dir"
    ):
        result = build_module_service_spec(
            metadata=metadata,
            module_name=module_name,
            known_module_names=[module_name],
            module_definition=schema,
            data_paths=resolve_experiment_data_paths(metadata),
        )
    return result, schema


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@given(module_name=_module_name)
def test_module_name_preserved(module_name):
    """result.module_name equals the module_name argument."""
    result, _ = _build(module_name)
    assert result.module_name == module_name


@given(module_name=_module_name)
def test_module_definition_identity(module_name):
    """result.module_definition is the exact schema object passed in (no copy or mutation)."""
    result, schema = _build(module_name)
    assert result.module_definition is schema


@given(module_name=_module_name, image_url=_image_url, image_tag=_image_tag)
def test_image_roundtrip(module_name, image_url, image_tag):
    """Parsed image URL and tag reconstruct the original image string."""
    image_str = f"{image_url}:{image_tag}"
    result, _ = _build(module_name, image=image_str)
    assert f"{result.image.image_url}:{result.image.image_tag}" == image_str
