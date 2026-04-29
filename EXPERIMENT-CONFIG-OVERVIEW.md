# Experiment Configuration file

This page is an overview of the `experiment-config.yml` file created by `feb setup`. This file is the core artifact of a FACTS2 experiment. 

 🚧 THIS PAGE IS UNDER CONSTRUCTION 🚧
 Check back soon for updates.

Content dumped from README to add here: 
> [!NOTE]
> If you copy and paste the `setup-new-experiment` command above, pass the paths to your input data directories via `--module-specific-inputs` and `--shared-inputs` (see [setup.md](setup.md)), or fill in those fields manually in the `experiment-config.yaml` that is created.

- If passed at the `uv run setup-new-experiment` step, values for `scenario`,`pyear-start/stop/step`,etc. will be prepopulated. If not, specify them here.
- You shouldn't need to make any more edits to this file but you can review to see the full experiment specification before generating a compose file.


#### 3. Specify workflows
Workflows are lists of sea-level modules that are passed to the totaling step. When `--total-all-modules` is set to `True`, a workflow is automatically created that includes all sea-level modules included in the experiment. You may also specify your own workflows with different sets of modules using the CLI prompts.

- If more than one sea-level module is specified, the CLI prompts the user for information about the workflows included in the experiment.
 
- Once completed, the program:
     - Makes a sub-directory in experiments with the supplied `--experiment-name` 
     - Creates and partially pre-populates an `experiment-config.yaml`. this is equivalent to a FACTS1 experiment `config.yml`. It is meant to be an abstract (run-environment agnostic), self-describing specification of the full experiment
     - `experiment-config.yaml` is pre-populated based on the arguments you supply and the modules you specified. Module default values are all propagated from each module's yaml file in the ModuleRegistry.
You will see the following output in your terminal window.
