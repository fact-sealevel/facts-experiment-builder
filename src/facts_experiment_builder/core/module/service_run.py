"""ServiceRun and ServiceDependency: how to run one module service, independent of the
backend that runs it."""

from dataclasses import dataclass

from facts_experiment_builder.core.module.module_schema import ModuleContainerImage


@dataclass(frozen=True)
class ServiceRun:
    """Everything needed to run one module service, independent of how it is run.

    Built by ModuleServiceSpec.to_service_run(). Backends format it into their own
    service description.
    """

    name: str  # service name, e.g. "fair-temperature" or "facts-total-wf1-global"
    image: ModuleContainerImage
    args: list[str]  # CLI flag list from _build_command_args()
    binds: list[str]  # "host:container" strings from _build_volumes()
    env: dict[str, str]  # env vars for inputs declared with `envvar`
    output_dir: str  # host output dir for this service
    # output arg name -> host path (shared output volume); all outputs, not filtered by
    # suppress_output_types, since other services may wait on any output this one writes
    host_outputs: dict[str, str]


@dataclass(frozen=True)
class ServiceDependency:
    """A service that must finish before another service runs.

    condition is set only when the module YAML's depends_on entry gives one; None means
    the backend's default (the dependency completed successfully).
    """

    service: str
    condition: str | None = None
