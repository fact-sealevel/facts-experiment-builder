"""Tests for the experiment_plan module."""

import pytest

from facts_experiment_builder.core.experiment.experiment_plan import (
    check_totaling_and_esl_have_workflows,
)
from facts_experiment_builder.core.workflow import Workflow

_ESL = ["extremesealevel-pointsoverthreshold"]
_WORKFLOWS = {"all-modules": Workflow(name="all-modules", module_names=["a"])}


@pytest.mark.parametrize(
    "sealevel,framework,esl,workflows",
    [
        ([], [], [], {}),  # supplied totaled data or no sea-level step
        (["a"], ["facts-total"], [], _WORKFLOWS),
        (["a"], ["facts-total"], _ESL, _WORKFLOWS),  # single module + ESL (#146)
        (["a", "b"], ["facts-total"], _ESL, _WORKFLOWS),
    ],
)
def test_check_totaling_and_esl_have_workflows_passes(
    sealevel, framework, esl, workflows
):
    check_totaling_and_esl_have_workflows(
        sealevel_module_names=sealevel,
        framework_module_names=framework,
        esl_module_names=esl,
        workflows=workflows,
    )


def test_check_raises_for_esl_without_sealevel_modules():
    with pytest.raises(ValueError, match="require sea-level modules"):
        check_totaling_and_esl_have_workflows(
            sealevel_module_names=[],
            framework_module_names=[],
            esl_module_names=_ESL,
            workflows={},
        )


@pytest.mark.parametrize("esl", [[], _ESL])
def test_check_raises_for_totaling_without_workflows(esl):
    """e.g. a single-module experiment set up before #146 was fixed."""
    with pytest.raises(ValueError, match="no workflows"):
        check_totaling_and_esl_have_workflows(
            sealevel_module_names=["a"],
            framework_module_names=["facts-total"],
            esl_module_names=esl,
            workflows={},
        )
