# Experiments

This page provides an overview of how facts-experiment-builder (FEB) works with the `experiments/` directory that is created in your facts workspace when you run `feb init`. This directory is where all experiments in your workspace are stored. An experiment is tied to a sub-directory whose name matches the name of the experiment. For example, an experiment named 'my_first_experiment' will look like this in your workspace:

```shell
facts_workspace/experiments/my_first_experiment
```

If you create an experiment with `feb setup-experiment`, this sub-directory is created automatically by the command. However, you can also manually create experiments by creating the named sub-directory and the `experiment-config.yaml` file that goes inside of it (which is also created by `feb setup-experiment`). 

## Example experiments

The FACTS project supplies a number of example experimenst which have been used for past reports and publications. They are stored in the [facts-experiment-catalog](https://github.com/fact-sealevel/facts-experiment-catalog). If you would like to run one of these example experiments, follow the steps below:
1. Find the experiment you'd like to replicate in the [experiment catalog](https://github.com/fact-sealevel/facts-experiment-catalog).
2. Create a sub-directory in `experiments/`, the name of which matches the name entered in the `experiment-name:` field in the experiment config file for that experiment's catalog entry. 
3. Download the experiment's `experiment-config.yaml` file from the catalog and place it in the experiment sub-directory you created. 