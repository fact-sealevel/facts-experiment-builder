

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import os

from facts_experiment_builder.adapters.module_adapter import ModuleParserFactory, load_metadata
from facts_experiment_builder.utils.setup_new_experiment import create_experiment_directory
from facts_experiment_builder.core.modules.fair.module import FairModule
from facts_experiment_builder.core.modules.bamber19_icesheets.module import Bamber19IcesheetsModule
@dataclass
class ExperimentManifest:
    """Structured representation of experiment manifest from metadata."""
    experiment_name: str
    temp_module: Optional[str] = None
    sealevel_modules: List[str] = None
    framework_modules: List[str] = None
    esl_modules: List[str] = None
    
    def __post_init__(self):
        if self.sealevel_modules is None:
            self.sealevel_modules = []
        if self.framework_modules is None:
            self.framework_modules = []
        if self.esl_modules is None:
            self.esl_modules = []
    
    def get_all_module_names(self) -> List[str]:
        """Get all module names from manifest."""
        modules = []
        if self.temp_module:
            modules.append(self.temp_module)
        modules.extend(self.sealevel_modules)
        modules.extend(self.framework_modules)
        modules.extend(self.esl_modules)
        return modules

@dataclass
class GlobalConfigOptions:
    """Global configuration options for an experiment."""
    pipeline_id: str
    scenario: str
    baseyear: int
    pyear_start: int
    pyear_end: int
    pyear_step: int
    nsamps: int

class Experiment:
    """A FACTS 2 experiment."""

    def __init__(self, 
                experiment_name: str,
                global_config_options: GlobalConfigOptions,
                ):
        self.experiment_name = experiment_name
        self.global_config_options = global_config_options
        self.check_experiment_dir()

    def check_experiment_dir(self) -> None:
        """Check if the experiment directory exists."""
        cwd = os.getcwd()

        if (Path(cwd).parent / "v2_experiments" / self.experiment_name).exists():
            raise FileExistsError(f"Experiment directory already exists: {Path(cwd).parent / 'v2_experiments' / self.experiment_name}. Is this a new experiment name?")

        if not (Path(cwd).parent / "v2_experiments" / self.experiment_name).exists():
            create_experiment_directory(self.experiment_name)
        self.experiment_dir = Path(cwd).parent / "v2_experiments" / self.experiment_name
    
    def add_temperature_module(self, module: str) -> None: #TODO don't think thi should take a string?
        """Add a temperature module to the experiment."""
        self.temperature_module = module
    def add_sealevel_module(self, module: Bamber19IcesheetsModule) -> None: #TODO don't want this to be specific to bamber
        """Add a sealevel module to the experiment."""
        self.sealevel_module = module
    
    #def format_experiment_dir(self) -> None:
        #"""Format the experiment directory."""
        #self.metadata_path = self.experiment_dir / "v2-experiment-metadata.yml"
        #if not self.metadata_path.exists():
        #    raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")
    @property
    def pipeline_id(self) -> str:
        return self.global_config_options.pipeline_id
    @property
    def scenario(self) -> str:
        return self.global_config_options.scenario
    @property
    def baseyear(self) -> int:
        return self.global_config_options.baseyear
    @property
    def pyear_start(self) -> int:
        return self.global_config_options.pyear_start
    @property
    def pyear_end(self) -> int:
        return self.global_config_options.pyear_end
    @property
    def pyear_step(self) -> int:
        return self.global_config_options.pyear_step
    @property
    def nsamps(self) -> int:
        return self.global_config_options.nsamps
    
class ExperimentParser:
    """Orchestrates module creation and Docker Compose generation for an experiment."""
    
    def __init__(self, 
                experiment: Experiment,
    ):
        self.experiment = experiment
        self.manifest = self.experiment.manifest
        self.modules: List[Any] = []
    
    def _parse_manifest(self) -> None:
        """Parse manifest from metadata."""
        # Handle both string and list formats
        temp_module = self.experiment.manifest.temp_module
        if isinstance(temp_module, list):
            temp_module = temp_module[0] if temp_module else None
        elif isinstance(temp_module, str):
            temp_module = temp_module.strip() if temp_module else None
        
        # Handle sealevel_modules - can be string or list
        sealevel_modules = self.metadata.get("sealevel_modules", [])
        if isinstance(sealevel_modules, str):
            sealevel_modules = [sealevel_modules.strip()]
        elif isinstance(sealevel_modules, list):
            sealevel_modules = [m.strip() if isinstance(m, str) else str(m) for m in sealevel_modules]
        
        # Handle framework_modules
        framework_modules = self.metadata.get("framework_modules", [])
        if isinstance(framework_modules, str):
            framework_modules = [framework_modules.strip()]
        elif isinstance(framework_modules, list):
            framework_modules = [m.strip() if isinstance(m, str) else str(m) for m in framework_modules]
        
        # Handle esl_modules
        esl_modules = self.metadata.get("esl_modules", [])
        if isinstance(esl_modules, str):
            esl_modules = [esl_modules.strip()]
        elif isinstance(esl_modules, list):
            esl_modules = [m.strip() if isinstance(m, str) else str(m) for m in esl_modules]
        
        return ExperimentManifest(
            experiment_name=self.metadata.get("experiment_name", "unknown"),
            temp_module=temp_module,
            sealevel_modules=sealevel_modules,
            framework_modules=framework_modules,
            esl_modules=esl_modules,
        )
    
    def create_modules(self) -> List[Any]:
        """
        Create module objects from manifest.
        
        Requires manifest fields (temp_module, sealevel_modules, etc.) to be
        specified in v2-experiment-metadata.yml.
        
        Returns:
            List of module instances
        
        Raises:
            ValueError: If no modules are specified in manifest
        """
        # Validate that manifest has at least one module specification
        has_manifest = (
            self.manifest.temp_module or
            self.manifest.sealevel_modules or
            self.manifest.framework_modules or
            self.manifest.esl_modules
        )
        
        if not has_manifest:
            raise ValueError(
                "No modules specified in manifest. "
                "Please specify at least one of: temp_module, sealevel_modules, "
                "framework_modules, or esl_modules in v2-experiment-metadata.yml"
            )
        
        modules = []
        
        # Create temp module
        if self.manifest.temp_module:
            try:
                module = ModuleParserFactory.create_module_from_metadata(
                    self.metadata_path,
                    module_type=self.manifest.temp_module
                )
                modules.append(module)
            except Exception as e:
                raise ValueError(
                    f"Failed to create temp module '{self.manifest.temp_module}' "
                    f"for experiment '{self.manifest.experiment_name}' "
                    f"(metadata: {self.metadata_path}): {e}"
                )
        
        # Create sealevel modules
        for module_name in self.manifest.sealevel_modules:
            try:
                module = ModuleParserFactory.create_module_from_metadata(
                    self.metadata_path,
                    module_type=module_name
                )
                modules.append(module)
            except Exception as e:
                raise ValueError(
                    f"Failed to create sealevel module '{module_name}' "
                    f"for experiment '{self.manifest.experiment_name}' "
                    f"(metadata: {self.metadata_path}): {e}"
                )
        
        # Create framework modules (if parsers exist)
        for module_name in self.manifest.framework_modules:
            try:
                module = ModuleParserFactory.create_module_from_metadata(
                    self.metadata_path,
                    module_type=module_name
                )
                modules.append(module)
            except Exception as e:
                print(
                    f"Warning: Framework module '{module_name}' not yet implemented "
                    f"for experiment '{self.manifest.experiment_name}' "
                    f"(metadata: {self.metadata_path}): {e}"
                )
                # Continue - framework modules may not have parsers yet
        
        # Create ESL modules (if parsers exist)
        for module_name in self.manifest.esl_modules:
            try:
                module = ModuleParserFactory.create_module_from_metadata(
                    self.metadata_path,
                    module_type=module_name
                )
                modules.append(module)
            except Exception as e:
                print(
                    f"Warning: ESL module '{module_name}' not yet implemented "
                    f"for experiment '{self.manifest.experiment_name}' "
                    f"(metadata: {self.metadata_path}): {e}"
                )
                # Continue - ESL modules may not have parsers yet
        
        self.modules = modules
        return modules
    
    def generate_compose_services(self) -> Dict[str, Any]:
        """
        Generate Docker Compose services for all modules.
        
        Returns:
            Dictionary of service_name -> service_config
        """
        if not self.modules:
            self.create_modules()
        
        services = {}
        for module in self.modules:
            # Generate compose service
            compose_service = module.generate_compose_service()
            
            # Use module name as service name (sanitize for Docker Compose)
            service_name = module.module_name.replace("-", "_") + "_service"
            services[service_name] = compose_service
        
        return services
    
    def generate_compose_file(
        self,
        output_path: Optional[Path] = None,
        version: str = "3.8"
    ) -> Dict[str, Any]:
        """
        Generate complete Docker Compose file.
        
        Args:
            output_path: Optional path to write compose file (defaults to experiment_dir/v2-compose.yaml)
            version: Docker Compose file version
        
        Returns:
            Complete compose file dictionary
        """
        services = self.generate_compose_services()
        
        compose_file = {
            "version": version,
            "services": services
        }
        
        # Write to file if path provided
        if output_path is None:
            output_path = self.experiment_dir / "v2-compose.yaml"
        
        with open(output_path, "w") as f:
            yaml.dump(compose_file, f, default_flow_style=False, sort_keys=False)
        
        return compose_file
    
    def get_manifest_summary(self) -> str:
        """Get a summary of the experiment manifest."""
        summary = f"Experiment: {self.manifest.experiment_name}\n"
        summary += f"  Temp module: {self.manifest.temp_module or 'None'}\n"
        summary += f"  Sealevel modules: {', '.join(self.manifest.sealevel_modules) or 'None'}\n"
        summary += f"  Framework modules: {', '.join(self.manifest.framework_modules) or 'None'}\n"
        summary += f"  ESL modules: {', '.join(self.manifest.esl_modules) or 'None'}\n"
        summary += f"  Total modules: {len(self.manifest.get_all_module_names())}"
        return summary


class ExperimentBuilder:
    """Python API for building experiments programmatically (without YAML).
    
    This is the programmatic equivalent of ExperimentParser, allowing you to
    create experiments and add modules directly in Python code instead of using
    YAML metadata files.
    """
    
    def __init__(self, experiment: Experiment):
        """
        Initialize the builder with an Experiment.
        
        Args:
            experiment: The Experiment object to build
        """
        self.experiment = experiment
        self.modules: List[Any] = []
        self.temp_module: Optional[Any] = None
        self.sealevel_modules: List[Any] = []
        self.framework_modules: List[Any] = []
        self.esl_modules: List[Any] = []
    
    def add_temperature_module(self, module: Any) -> 'ExperimentBuilder':
        """
        Add a temperature module to the experiment.
        
        Args:
            module: A temperature module instance (e.g., FairModule)
            
        Returns:
            self for method chaining
        """
        if self.temp_module is not None:
            raise ValueError("Temperature module already added. Only one temperature module allowed.")
        self.temp_module = module
        self.modules.append(module)
        return self
    
    def add_sealevel_module(self, module: Any) -> 'ExperimentBuilder':
        """
        Add a sea-level module to the experiment.
        
        Args:
            module: A sea-level module instance (e.g., Bamber19IcesheetsModule)
            
        Returns:
            self for method chaining
        """
        self.sealevel_modules.append(module)
        self.modules.append(module)
        return self
    
    def add_framework_module(self, module: Any) -> 'ExperimentBuilder':
        """
        Add a framework module to the experiment.
        
        Args:
            module: A framework module instance
            
        Returns:
            self for method chaining
        """
        self.framework_modules.append(module)
        self.modules.append(module)
        return self
    
    def add_esl_module(self, module: Any) -> 'ExperimentBuilder':
        """
        Add an ESL module to the experiment.
        
        Args:
            module: An ESL module instance
            
        Returns:
            self for method chaining
        """
        self.esl_modules.append(module)
        self.modules.append(module)
        return self
    
    def get_modules(self) -> List[Any]:
        """
        Get all modules added to the experiment.
        
        Returns:
            List of all module instances
        """
        return self.modules
    
    def generate_compose_services(self) -> Dict[str, Any]:
        """
        Generate Docker Compose services for all modules.
        
        Returns:
            Dictionary of service_name -> service_config
        """
        if not self.modules:
            raise ValueError("No modules added to experiment. Add at least one module before generating compose services.")
        
        services = {}
        for module in self.modules:
            # Generate compose service
            compose_service = module.generate_compose_service()
            
            # Use module name as service name (sanitize for Docker Compose)
            service_name = module.module_name.replace("-", "_") + "_service"
            services[service_name] = compose_service
        
        return services
    
    def generate_compose_file(
        self,
        output_path: Optional[Path] = None,
        version: str = "3.8"
    ) -> Dict[str, Any]:
        """
        Generate complete Docker Compose file.
        
        Args:
            output_path: Optional path to write compose file (defaults to experiment_dir/v2-compose.yaml)
            version: Docker Compose file version
        
        Returns:
            Complete compose file dictionary
        """
        services = self.generate_compose_services()
        
        compose_file = {
            "version": version,
            "services": services
        }
        
        # Write to file if path provided
        if output_path is None:
            output_path = self.experiment.experiment_dir / "v2-compose.yaml"
        
        with open(output_path, "w") as f:
            yaml.dump(compose_file, f, default_flow_style=False, sort_keys=False)
        
        return compose_file
    
    def to_yaml(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate YAML metadata file from the experiment builder state.
        
        This allows you to export a programmatically-created experiment to YAML
        format for later use with ExperimentParser.
        
        Args:
            output_path: Optional path to write YAML file (defaults to experiment_dir/v2-experiment-metadata.yml)
        
        Returns:
            Metadata dictionary
        """
        if output_path is None:
            output_path = self.experiment.experiment_dir / "v2-experiment-metadata.yml"
        
        # Build metadata structure
        metadata = {
            "experiment_name": self.experiment.experiment_name,
            "pipeline-id": self.experiment.pipeline_id,
            "scenario": self.experiment.scenario,
            "baseyear": self.experiment.baseyear,
            "pyear_start": self.experiment.pyear_start,
            "pyear_end": self.experiment.pyear_end,
            "pyear_step": self.experiment.pyear_step,
            "nsamps": self.experiment.nsamps,
            "seed": getattr(self.experiment.global_config_options, 'seed', 1234),
        }
        
        # Add module specifications
        if self.temp_module:
            metadata["temp_module"] = self.temp_module.module_name
        
        if self.sealevel_modules:
            metadata["sealevel_modules"] = [m.module_name for m in self.sealevel_modules]
        
        if self.framework_modules:
            metadata["framework_modules"] = [m.module_name for m in self.framework_modules]
        
        if self.esl_modules:
            metadata["esl_modules"] = [m.module_name for m in self.esl_modules]
        
        # Write to file
        with open(output_path, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
        
        return metadata
    
    def get_summary(self) -> str:
        """Get a summary of the experiment."""
        summary = f"Experiment: {self.experiment.experiment_name}\n"
        summary += f"  Temp module: {self.temp_module.module_name if self.temp_module else 'None'}\n"
        summary += f"  Sealevel modules: {', '.join([m.module_name for m in self.sealevel_modules]) or 'None'}\n"
        summary += f"  Framework modules: {', '.join([m.module_name for m in self.framework_modules]) or 'None'}\n"
        summary += f"  ESL modules: {', '.join([m.module_name for m in self.esl_modules]) or 'None'}\n"
        summary += f"  Total modules: {len(self.modules)}"
        return summary

