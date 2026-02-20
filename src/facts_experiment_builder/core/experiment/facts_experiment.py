"""In-memory representation of an experiment (analogous to experiment-metadata.yml)."""
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from facts_experiment_builder.infra.path_manager import find_project_root


# Keys that appear in experiment-metadata.yml (for parsing and round-trip)
TOP_LEVEL_PARAM_KEYS = [
    "pipeline-id", "scenario", "baseyear", "pyear_start", "pyear_end",
    "pyear_step", "nsamps", "seed",
]
MANIFEST_KEYS = [
    "temperature_module", "sealevel_modules", "framework_modules", "esl_modules",
]
PATH_KEYS_PRIMARY = [
    "general-input-data", "module-specific-input-data",
    "output-data-location", "location-file",
]
PATH_KEYS_ALTERNATIVES = {
    "general-input-data": ["general_input_data"],
    "module-specific-input-data": ["module_specific_input_data"],
    "output-data-location": ["output_data_location", "output-path", "output_path"],
    "location-file": ["location_file"],
}
FINGERPRINT_PARAM_KEYS = [
    "fingerprint-dir",
    "location-file"
]

class FactsExperiment:
    """
    In-memory representation of an experiment (analoguous to experiment-metadata.yml).
    Used to generate run-environment artifacts (e.g. experiment-compose.yaml).
    Loaded from or written to experiment-metadata.yml.
    """

    def __init__(
        self,
        experiment_name: str,
        top_level_params: Dict[str, Any],
        manifest: Dict[str, Any],
        paths: Dict[str, Any],
        fingerprint_params: Dict[str, Any],
        module_sections: Dict[str, Dict[str, Any]],
        extra: Optional[Dict[str, Any]] = None,
        ):
        self._experiment_name = experiment_name
        self._top_level_params = dict(top_level_params)
        self._manifest = dict(manifest)
        self._paths = dict(paths)
        self._fingerprint_params = dict(fingerprint_params)
        self._module_sections = dict(module_sections)
        self._extra = dict(extra) if extra is not None else {}

        # Optional validation, e.g. require manifest keys
        if "temperature_module" not in self._manifest:
            self._manifest["temperature_module"] = None
        if "sealevel_modules" not in self._manifest:
            self._manifest["sealevel_modules"] = []

    # Expose as read-only if you want “immutable” semantics
    @property
    def experiment_name(self) -> str:
        """Name of this experiment."""
        return self._experiment_name

    @property
    def top_level_params(self) -> Dict[str, Any]:
        """Top-level parameters that are shared across modules, though this can optionally be overridden. 
        These include (pipeline-id, scenario, baseyear, pyear_start, pyear_end, pyear_step, nsamps, seed).
        """
        return self._top_level_params

    @property
    def manifest(self) -> Dict[str, Any]:
        """Manifest of the modules included in this experiment. This includes (temperature_module, sealevel_modules, framework_modules, esl_modules).
        """
        return self._manifest

    @property
    def paths(self) -> Dict[str, Any]:
        """Paths to the input and output data for this experiment. 
        This includes (general-input-data, module-specific-input-data, output-data-location, location-file).
        ^^ TODO double check this list is accurate
        """
        return self._paths

    @property
    def fingerprint_params(self) -> Dict[str, Any]:
        """Fingerprint parameters that are shared across modules, though this can optionally be overridden.
        These include (fingerprint-dir, location-file).
        """
        return self._fingerprint_params

    @property
    def module_sections(self) -> Dict[str, Dict[str, Any]]:

        return self._module_sections

    @property
    def extra(self) -> Dict[str, Any]:
        return self._extra

    @classmethod
    def from_metadata_dict(cls, metadata: Dict[str, Any]) -> "FactsExperiment":
        """Build a FactsExperiment from the metadata dict shape (e.g. from YAML)."""
        experiment_name = metadata.get("experiment_name", "")

        top_level_params = {
            k: metadata[k] for k in TOP_LEVEL_PARAM_KEYS if k in metadata
        }
        fingerprint_params = {
            k: metadata[k] for k in FINGERPRINT_PARAM_KEYS if k in metadata
        }
        manifest = {
            "temperature_module": metadata.get("temperature_module"),
            "sealevel_modules": metadata.get("sealevel_modules", []),
            "framework_modules": metadata.get("framework_modules", []),
            "esl_modules": metadata.get("esl_modules", []),
        }
        if isinstance(manifest["sealevel_modules"], str):
            manifest["sealevel_modules"] = [manifest["sealevel_modules"]]

        paths_normalized = {}
        for primary in PATH_KEYS_PRIMARY:
            value = metadata.get(primary)
            if value is None and primary in PATH_KEYS_ALTERNATIVES:
                for alt in PATH_KEYS_ALTERNATIVES[primary]:
                    value = metadata.get(alt)
                    if value is not None:
                        break
            if value is not None:
                # Preserve clue/value dict for template (from create_new)
                if isinstance(value, dict) and "clue" in value:
                    paths_normalized[primary] = value
                else:
                    if isinstance(value, dict) and "value" in value:
                        value = value["value"]
                    if isinstance(value, str):
                        paths_normalized[primary] = value

        excluded = set(TOP_LEVEL_PARAM_KEYS) | set(FINGERPRINT_PARAM_KEYS) | set(MANIFEST_KEYS) | set(PATH_KEYS_PRIMARY)
        excluded |= set().union(*(PATH_KEYS_ALTERNATIVES.get(k, []) for k in PATH_KEYS_PRIMARY))
        excluded.add("experiment_name")

        module_sections = {
            k: v for k, v in metadata.items()
            if k not in excluded and isinstance(v, dict)
        }

        extra = {
            k: v for k, v in metadata.items()
            if k not in top_level_params and k not in manifest and k not in paths_normalized
            and k not in fingerprint_params and k not in module_sections and k != "experiment_name"
        }

        return cls(
            experiment_name=experiment_name,
            top_level_params=top_level_params,
            manifest=manifest,
            paths=paths_normalized,
            fingerprint_params=fingerprint_params,
            module_sections=module_sections,
            extra=extra,
        )

    @classmethod
    def create_new_experiment_obj(
        cls,
        experiment_name: str,
        temperature_module: str,
        sealevel_modules: List[str],
        framework_modules: List[str] = None,
        extremesealevel_module: str = None,
        experiment_path: Path = None,
        *,
        pipeline_id: Optional[str] = None,
        scenario: Optional[str] = None,
        baseyear: Optional[int] = None,
        pyear_start: Optional[int] = None,
        pyear_end: Optional[int] = None,
        pyear_step: Optional[int] = None,
        nsamps: Optional[int] = None,
        seed: Optional[int] = None,
        location_file: Optional[str] = None,
        fingerprint_dir: Optional[str] = None,
        create_metadata_bundle: Callable[[str, Any], Dict[str, Any]],
        format_module_from_definition: Callable[[Any], Dict[str, Any]],
        load_facts_module_by_name: Callable[[str, Path], Any],
        find_project_root: Callable[[], Path],
        top_level_param_clues: Dict[str, str],
        ) -> "FactsExperiment":
        """
        Create a new experiment from template/CLI inputs.
        Dependencies are injected to avoid circular imports (call from application layer).
        """
        #First, create dict and fill with top level param keys 
        #and their clues/values from top_level_param_clues 
        # TODO top_level_param_clues currently hardcoded in setup_new_experiment
        # need to fix this. others are hardcoded at top of this script.

        metadata = {
            "experiment_name": experiment_name,
            "pipeline-id": create_metadata_bundle(top_level_param_clues.get("pipeline-id", "Pipeline ID"), pipeline_id),
            "scenario": create_metadata_bundle(top_level_param_clues.get("scenario", "Emissions scenario name"), scenario),
            "baseyear": create_metadata_bundle(top_level_param_clues.get("baseyear", "Base year"), baseyear),
            "pyear_start": create_metadata_bundle(top_level_param_clues.get("pyear_start", "Projection year start"), pyear_start),
            "pyear_end": create_metadata_bundle(top_level_param_clues.get("pyear_end", "Projection year end"), pyear_end),
            "pyear_step": create_metadata_bundle(top_level_param_clues.get("pyear_step", "Projection year step"), pyear_step),
            "nsamps": create_metadata_bundle(top_level_param_clues.get("nsamps", "Number of samples"), nsamps),
            "seed": create_metadata_bundle(top_level_param_clues.get("seed", "Random seed to use for sampling"), seed),
            "temperature_module": temperature_module,
            "sealevel_modules": sealevel_modules if len(sealevel_modules) > 1 else (sealevel_modules[0] if sealevel_modules else []),
            "framework_modules": framework_modules ,
            "esl_modules": extremesealevel_module ,
            "module-specific-input-data": create_metadata_bundle("Module-specific input data"),
            "general-input-data": create_metadata_bundle("General input data"),
            "location-file": create_metadata_bundle("Location file", location_file),
            "fingerprint-dir": create_metadata_bundle("Fingerprint directory", fingerprint_dir),
            "output-data-location": create_metadata_bundle(
                top_level_param_clues.get("output-data-location", "Output path"),
                f"./experiments/{experiment_name}/data/output",
            ),
        }
        #Find project root (dir w/ pyproject.toml)
        project_root = find_project_root()
        #Load the module definition files for the specified temperature module, if any
        #uses fn from facts_module.py
        if temperature_module and temperature_module.upper() != "NONE":
            try:
                mod_def = load_facts_module_by_name(temperature_module, project_root)
                metadata[temperature_module] = format_module_from_definition(mod_def)
            except Exception:
                pass
        #Same for sealevel modules
        for mod in sealevel_modules:
            try:
                mod_def = load_facts_module_by_name(mod, project_root)
                metadata[mod] = format_module_from_definition(mod_def)
            except Exception:
                pass
        if framework_modules:
            for mod in framework_modules:
                try:
                    mod_def = load_facts_module_by_name(mod, project_root)
                    metadata[mod] = format_module_from_definition(mod_def)
                except Exception:
                    pass
        if extremesealevel_module:
            for mod in extremesealevel_module:
                try:
                    mod_def = load_facts_module_by_name(mod, project_root)
                    metadata[mod] = format_module_from_definition(mod_def)
                except Exception:
                    pass
        # Remove None values but preserve comment keys
        def remove_none(d: Any) -> Any:
            if isinstance(d, dict):
                return {k: remove_none(v) for k, v in d.items() if v is not None or (isinstance(k, str) and k.startswith("#"))}
            if isinstance(d, list):
                return [remove_none(item) for item in d]
            return d
        metadata = remove_none(metadata)
        return cls.from_metadata_dict(metadata)

    def merge_defaults_for_module(
        self,
        module_name: str,
        defaults_yml: Dict[str, Any],
        module_def: Optional[Any],
        *,
        create_metadata_bundle: Callable[[str, Any], Dict[str, Any]],
        get_clue_from_module_yaml: Callable[[Any, str, str], str],
        is_metadata_value: Callable[[Any], bool],
        ) -> None:
        """
        Merge defaults from defaults_yml into this experiment's module section.

        Updates the experiment's in-memory module section for the given module
        with values from the module's defaults file. Handles ``inputs``,
        ``options``, and ``image`` sections; keys are matched with flexible
        naming (snake_case, kebab-case). I/O and module loading stay in the
        application layer; this method only mutates in-memory state.

        Parameters
        ----------
        module_name : str
            Name of the module whose section to update (e.g. ``"fair-temperature"``).
        defaults_yml : dict
            Parsed contents of the module's defaults YAML (e.g. from
            ``defaults_<module>.yml``). May contain ``inputs``, ``options``,
            and ``image`` keys.
        module_def : object or None
            Loaded module definition (e.g. FactsModule) used to look up
            clue/help text for keys; can be None if not available.
        create_metadata_bundle : callable
            Function (clue, value) -> dict used to build clue/value entries
            for the metadata.
        get_clue_from_module_yaml : callable
            Function (module_def, section_key, key) -> str used to get
            help text from the module YAML for a given key.
        is_metadata_value : callable
            Function (value) -> bool used to detect existing clue/value
            dicts so only the ``value`` is updated in place.

        Returns
        -------
        None
            This method mutates ``self._module_sections[module_name]``
            in place and returns nothing.

        Notes
        -----
        I/O and module loading are the responsibility of the application
        layer; this method assumes ``defaults_yml`` and ``module_def``
        are already loaded.
        """
        if not defaults_yml:
            return
        if module_name not in self._module_sections:
            self._module_sections[module_name] = {}
        section = self._module_sections[module_name]
        for section_key, section_defaults in defaults_yml.items():
            if section_key not in section:
                if section_key in ("inputs", "options"):
                    section[section_key] = {}
                elif section_key == "image":
                    section[section_key] = ""
                else:
                    continue
            current_section = section[section_key]
            if isinstance(section_defaults, dict) and isinstance(current_section, dict):
                comment_keys = {k: v for k, v in current_section.items() if isinstance(k, str) and k.startswith("#")}
                for nested_key, nested_default in section_defaults.items():
                    matching_key = None
                    if nested_key in current_section:
                        matching_key = nested_key
                    else:
                        snake = nested_key.replace("-", "_")
                        if snake in current_section:
                            matching_key = snake
                        else:
                            kebab = nested_key.replace("_", "-")
                            if kebab in current_section:
                                matching_key = kebab
                    if matching_key:
                        nested_current = current_section[matching_key]
                        if is_metadata_value(nested_current):
                            nested_current["value"] = nested_default
                        elif nested_current is None or nested_current == "":
                            clue = None
                            if module_def and section_key in ("inputs", "options"):
                                clue = get_clue_from_module_yaml(module_def, section_key, matching_key)
                            current_section[matching_key] = create_metadata_bundle(clue or f"add your {matching_key} here", nested_default)
                        else:
                            current_section[matching_key] = create_metadata_bundle(f"add your {matching_key} here", nested_default)
                    else:
                        snake_case_key = nested_key.replace("-", "_")
                        kebab_case_key = nested_key.replace("_", "-") if "_" in nested_key else nested_key
                        if snake_case_key in current_section:
                            nc = current_section[snake_case_key]
                            if is_metadata_value(nc):
                                nc["value"] = nested_default
                            else:
                                current_section[snake_case_key] = create_metadata_bundle(f"add your {snake_case_key} here", nested_default)
                        elif kebab_case_key in current_section and kebab_case_key != nested_key:
                            nc = current_section[kebab_case_key]
                            if is_metadata_value(nc):
                                nc["value"] = nested_default
                            else:
                                current_section[kebab_case_key] = create_metadata_bundle(f"add your {kebab_case_key} here", nested_default)
                        else:
                            clue = None
                            if module_def and section_key in ("inputs", "options"):
                                clue = get_clue_from_module_yaml(module_def, section_key, snake_case_key) or get_clue_from_module_yaml(module_def, section_key, nested_key)
                            current_section[snake_case_key] = create_metadata_bundle(clue or f"add your {snake_case_key} here", nested_default)
                for ck, cv in comment_keys.items():
                    if ck not in current_section:
                        current_section[ck] = cv
            elif section_key == "image" and isinstance(section_defaults, dict):
                image_url = section_defaults.get("image_url")
                if image_url:
                    section[section_key] = image_url




