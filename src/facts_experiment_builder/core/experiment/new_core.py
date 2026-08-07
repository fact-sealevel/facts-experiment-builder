"""Starting with domain rules/fns of a FACTS experiment."""

from dataclasses import dataclass, field
import dataclasses
from typing import Union, Literal, List, ClassVar
from datetime import datetime
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class ModuleSchema:
    """Module schema data class."""

    module_name: str
    ...


# ---------- global params level domain objects----------
"""This new (streamlined) version of core works off the following domain model:
- An Experiment is compose of ExperimentName, GlobalParams, ExperimentStructure, Workflows and a ModulesSection
    - This loosely corresponds to an exp config but more importantly, is the full conceptual specification of a facts experiment
- GlobalParams is dataclass holding nsamps, scenario, pyear start/stop/step, baseyear, etc.
- ExperimentStructure is a dataclass that holds a list of experiment Step objects
- there is the generic Step(ABC) 
"""
@dataclass(frozen=True)
class Name:
    experiment_name: str


@dataclass(frozen=True)
class GlobalParams:
    pyear_start: int
    pyear_end: int
    pyear_step: int
    nsamps: int
    scenario: str
    baseyear: int
    projection_scale: str
    date_created: str

# ---------- experiment structure/step level domain objects ---------
# Steps have an associated name (can be anything) and action (is a module run or data passed)
@dataclass(frozen=True)
class RunModule:
    """One or more modules is run in an experiment step."""

    kind: Literal["module"]


@dataclass(frozen=True)
class PassData:
    """Data is passed in place of running modules in experiment step."""

    kind: Literal["data"]

@dataclass(frozen=True)
class RunModulePerWorkflow:
    """Dataclass to represent an experiment step where a module is run once for each
    workflow (add projection scale too?)"""

    kind: Literal["module_per_workflow"]

# this is the ABC for any kind of step.
# subclasses of it represent steps that have module action and data action
@dataclass(frozen=True)
class Step(ABC):
    """Dataclass representing an individual experiment step.

    Contains a name which is used to reference it and `action`, the action which occurs
    at the step
    """

    name: str
    action: ClassVar[str]

    @property
    @abstractmethod
    def included_modules(self) -> list[str] | None: ...

    action: Union[PassData, RunModule, RunModulePerWorkflow]

@dataclass(frozen=True)
class DataStep(Step):
    action: ClassVar[Literal["pass_data"]]  # PassData

    @property
    def included_modules(self) -> None:
        return None

@dataclass(frozen=True)
class ModuleStep(Step):
    module_names: list[str]
    action: ClassVar[Literal["run_module"]] = "run_module"  # "RunModule"

    @property
    def included_modules(self) -> list[str]:
        return self.module_names
@dataclass(frozen=True)
class ModulePerWorkflowStep(Step):
    module_names: list[str]
    action: ClassVar[Literal["run_module_per_workflow"]] = "run_module_per_workflow"

    @property
    def included_modules(self) -> list[str]:
        return self.module_names

# ---- more specific step types ----
# not sure where this goes yet, but wanted to start mapping out the different
# types of scientific steps that can exist in an experiment.
# I think there should be a mapping between module names and scientific module type (would req. change in module yaml)
# so that when a module is specified, it automatically corresponds to a type of step ? 

@dataclass(frozen=True)
class ClimateStep(ModuleStep):
    ...

@dataclass(frozen=True)
class GMSLStep(ModuleStep):
    depends_on_climate_step: bool
    ...

@dataclass(frozen=True)
class FingerprintingStep:
    depends_on_gmsl_step: bool = True
    ...

# --------- experiment structure ---------
# this is kind of like the manifest/skeleton. it holds all of hte steps in an experiment
@dataclass(frozen=True)
class Structure:
    """Data class to hold the structure of an experiment (What steps are in the
    experiment)"""

    name: Name
    steps: list[Step] = field(default_factory=list)

    def list_all_modules(self) -> List:
        """Walk through steps and list all modules included in experiment."""
        modules_ls = []
        for step in self.steps:
            if step.action != "run_module":
                pass
            # extract list of module names for that step
            modules_in_this_step = step.included_modules
            # add to overall list
            for m in modules_in_this_step:
                modules_ls.append(m)
        return modules_ls

    def add_step(self, step: Step) -> "Structure":
        """Method to add a new step to a Structure.

        Returns a new Strucutre object with the added steps.
        """
        return dataclasses.replace(self, steps=[*self.steps, step])

# ------------ domain objects related to workflows --------------
@dataclass(frozen=True)
class SingleWorkflow:
    """"Data class to hold a single workflow and its name."""

    name: str
    modules_in_workflow: list


@dataclass(frozen=True)
class WorkflowCollection:
    """Dataclass to hold workflows dict."""

    workflows: dict[str, SingleWorkflow]

    def add_workflow(self, workflow_name: str, workflow_obj: SingleWorkflow):
        """Add a single workflow to collection of workflows."""
        self.workflows.update({workflow_name, workflow_obj})

# ------------ domain objects related to individual modules in an experiment (ie their schemas/second half of an exp config yaml)
@dataclass(frozen=True)
class ModulesSection:
    """Data class to hold module-specific information section of experiment (should be a
    moduleschema for each module in experiment)"""

    module_schemas: list[ModuleSchema]

# ------------- highest level domain object. 
# represents entire experiment, holds all of the smaller
# objects defined above
@dataclass(frozen=True)
class Experiment:
    """Data class to hold all of the component sections that make a complete FACTS
    experiment."""

    experiment_name: Name
    global_params: GlobalParams
    structure: Structure
    workflows: WorkflowCollection
    modules_section: ModulesSection


# ------------ intent objs (should tech. live in application?) --------
@dataclass(frozen=True)
class StepSpec:
    """Declarative desc.

    of a step to create. cli input is translated into a stepspec object.
    """

    name: str
    action: str  # must match a Step subclass' `action` tag ("run_module","pass_data","run_module_per_workflow")
    kwargs: dict = field(
        default_factory=dict
    )  # holds any params that are specific to a given step


# ------------ domain functions --------
def specify_experiment_name(name: str) -> Name:
    """Specify a name for an experiment."""
    return Name(experiment_name=name)

def specify_global_params(
    pyear_start: int,
    pyear_step: int,
    pyear_end: int,
    baseyear: int,
    scenario: str,
    nsamps: int,
    projection_scale: str,
) -> GlobalParams:
    """Specify global parameters for an experiment."""
    return GlobalParams(
        pyear_start=pyear_start,
        pyear_step=pyear_step,
        pyear_end=pyear_end,
        scenario=scenario,
        baseyear=baseyear,
        nsamps=nsamps,
        projection_scale=projection_scale,
        date_created=datetime.now(),
    )

_STEP_TYPES: dict[str, type[Step]] = {
    cls.action for cls in (DataStep, ModuleStep, ModulePerWorkflowStep)
}
def create_step(step_name: str, step_action: str, **kwargs) -> Step:
    """Create a step that can be added to an experiment structure."""
    try:
        step_cls = _STEP_TYPES[step_action]
    except KeyError:
        raise ValueError(f"Expected valid step action, received: {step_action}")
    return step_cls(name=step_name, **kwargs)

def create_structure(experiment_name: str) -> Structure:
    """Function to create an empty structure for an experiment given an experiment
    name."""
    name = Name(experiment_name=experiment_name)
    return Structure(name=name)

def build_structure(
    experiment_name: str,
    step_specs: list[StepSpec],
) -> Structure:
    """Function to create a structure and populate it with steps based on
    list[StepSpecs]"""
    structure = create_structure(experiment_name=experiment_name)
    for spec in step_specs:
        step = create_step(step_name=spec.name, step_action=spec.action, **spec.kwargs)
        structure = structure.add_step(step)
    return structure

def create_single_workflow(
    workflow_name: str, workflow_modules: List[str]
) -> SingleWorkflow:
    """Fn to create a SingleWorkflow object.

    Accepts: name of workflow, list of modules to include in workflow.
    Returns: SingleWorkflow
    """
    return SingleWorkflow(name=workflow_name, modules_in_workflow=workflow_modules)

def make_single_module_section(module_name: str) -> ModuleSchema:
    return ModuleSchema(module_name=module_name)

def make_modules_section(list_of_modules: list[str]) -> ModulesSection:
    schema_list = []
    for module in list_of_modules:
        schema = make_single_module_section(module_name=module)
        schema_list.append(schema)
    return ModulesSection(module_schemas=schema_list)


def build_experiment(
    experiment_name: str,
    global_params: GlobalParams,
    structure: Structure,
    workflows: WorkflowCollection,
) -> Experiment:
    name = Name(experiment_name)
    # Make list of modules from structure
    modules_list = structure.list_all_modules()
    modules_section = make_modules_section(list_of_modules=modules_list)

    experiment = Experiment(
        experiment_name=name,
        global_params=global_params,
        structure=structure,
        workflows=workflows,
        modules_section=modules_section,
    )
    return experiment
