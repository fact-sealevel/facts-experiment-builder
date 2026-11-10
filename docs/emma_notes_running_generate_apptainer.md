# notes from trying to run `generate-apptainer` 

- from `facts2-workspace`, enter shell session using lima apptainer template
```shell
limactl start apptainer
limactl shell apptainer
```

- `facts2-workspace` is already setup to run docker compose experiments (ie. it has `./data/shared_data` and `./data/module_specific_data`)
(I needed to modify `~/.lima/apptainer/lima.yaml` to add a mount to `v2_experiments`)

- outside of the vm, i ran `uv run feb generate-apptainer` for a pre-existing experiment (v2_experiments/my_facts_experiment)
NOTE: need to think about how/where experiment output is written. with only one implementation (docker compose), experiments always wrote to `experiment_name_dir/output`. If we start to allow multiple run files per experiment (ie. a docker compose and a apptainer bash script), need a way to keep track of and keep separate those outputs. maybe `generate-compose` could create/use a `compose_output` dir and `generate-apptainer` could create/use a `apptainer_output` dir, both of which are in the experiment parent dir? if someone tries to re-run an experiment that already has data in the corresponding output dir, what happens? what hsould happen? maybe experiment or output dirs should have a timestamp or a pipeline id in the name to make them more unique? 