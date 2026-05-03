# For contributors

This page contains additional information about the internal structure of facts-experiment-builder and how it interfaces with module in the FACTS2 ecosystem. It is intended for users who may be interested in contributing to the project or in submitting their own module to the FACTS2 ecosystem that could be used by users of FEB.

This package centers around physical artifacts, YAML files, and core in-memory representations of the artifacts. For example, an experiment is abstractly defined as a set of parameters, a collection of modules, and a list of workflows. This is store on disk as an `experiment-config.yaml` file and represented in-memory by the `FactsExperiment` class. 

Each containerized module application has a corresponding module yaml file (ie. `bamber19_icesheets_module.yaml` or `tlm_sterodynamics_module.yaml`). The module yaml represents all of the inputs, outputs, and parameters used to specify that module as well as other critical metadata. In memory, this is stored as an object of the `ModuleSchema` class. Default values for parameters and filenames for input and output files are also stored in the module yaml files.
