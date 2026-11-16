# Experiments

This page provides an overview of how facts-experiment-builder (FEB) works in your FACTS workspace. When you run `feb init`, a `experiments/` directory is automatically created in your working directory (which we call your 'facts workspace'). `experiments/` is the standard location to hold experiments but you can create additional directories to hold different groups of experiments if that is helpful in your workflow. 

When you create an experiment, you pass the name of the parent directory with the name of the experiment (`--experiment-name experiments/example_experiment)`. FEB does not require that you include a parent directory but it is recommended instead of placing individual experiments directly in your FACTS workspace. If you want to use an alternate name for the parent directory (ie. `new_experiments`), you must manually create the directory before running `feb setup-experiment`. For example, an experiment named `experiments/my_first_experiment` will look like this in your workspace:

```shell
./facts_workspace/experiments/my_first_experiment
```

If you create an experiment with `feb setup-experiment`, the experiment-level sub-directory (`my_first_experiment`) is created automatically by the command. However, you can also manually create experiments by creating the named sub-directory and the `experiment-config.yaml` file that goes inside of it (which is also created by `feb setup-experiment`). 

`feb setup-experiment` also writes a `README.md` to the experiment sub-directory. It records how the experiment was created: the full `setup-experiment` command, with every option and its value (defaults included), the FEB version, the creation time and the experiment's workflows. Use it to set up the same experiment again. The README is only a record: FEB doesn't read it, so an experiment created by hand doesn't need one.

```shell
./facts_workspace/experiments/my_first_experiment
├── experiment-config.yaml    # defines the experiment; written by setup-experiment, completed by you
└── README.md                 # how the experiment was created; written by setup-experiment
```

## Example experiments

The FACTS project supplies a number of example experiments which have been used for past reports and publications. They are stored in the [facts-experiment-catalog](https://github.com/fact-sealevel/facts-experiment-catalog). If you would like to run one of these example experiments, follow the steps below:
1. Find the experiment you'd like to replicate in the [experiment catalog](https://github.com/fact-sealevel/facts-experiment-catalog).
2. Create a sub-directory in `experiments/`, the name of which matches the name entered in the `experiment-name:` field in the experiment config file for that experiment's catalog entry. 
3. Download the experiment's `experiment-config.yaml` file from the catalog and place it in the experiment sub-directory you created. 

> [!HINT]
> We recommend starting with the example-coupling-ssp126 [experiment](https://github.com/fact-sealevel/facts-experiment-catalog/tree/main/example-coupling-ssp126-260720) listed in the experiment catalog.