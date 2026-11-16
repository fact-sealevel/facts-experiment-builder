"""ApptainerServiceSpec: thin data carrier for one Apptainer run_service block."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApptainerServiceSpec:
    """All information needed to emit one Apptainer run_service block.

    Built by ModuleServiceSpec.generate_apptainer_service().
    Consumed by the apptainer_experiment.sh.j2 template.

    sif_name = f"{service_name}-{image_tag}" (versioned, e.g. "fair-temperature-0.2.1").
    image_name may differ from service_name when multiple services share one image
    (e.g. "ipccar5-glaciers" and "ipccar5-icesheets" both have image_name "ipccar5").
    """

    service_name: str  # module name used as SIF stem, e.g. "fair-temperature"
    image_name: str  # last path segment of image_url, e.g. "ipccar5"
    image_tag: str  # e.g. "0.2.1"
    binds: list[str]  # raw "host:container" strings; template prepends "--bind="
    args: list[str]  # CLI flag list from _build_command_args()
    wait_for_files: list[str]  # absolute host paths to poll before running (Stage 2)
    run_in_background: bool  # True for facts-total parallel jobs (Stage 3)
    pid_var: str | None  # e.g. "PID_WF1F_GLOBAL"; None when not background
    output_dir: str  # host output dir for this service (mkdir'd by the script)
    registry: str  # image_url minus its last segment, e.g. "ghcr.io/fact-sealevel"; "" if none
    host_outputs: dict[str, str]  # output arg name -> host path (shared output volume)
    # env vars for inputs declared with `envvar` (Compose `environment:`)
    env: dict[str, str]

    @property
    def image_ref(self) -> str:
        """Full image reference to pull, e.g. "ghcr.io/fact-sealevel/ipccar5:0.1.2".

        Each service uses its own registry, so modules may come from different ones.
        """
        image = (
            f"{self.registry}/{self.image_name}" if self.registry else self.image_name
        )
        return f"{image}:{self.image_tag}"
