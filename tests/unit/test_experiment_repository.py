# def test_experiment_repository_can_save_experiment(session):
#     experiment = ExperimentConfig(
#         experiment_name="test-exp",
#         date_created="2026-08-05",
#         projection_scale="local",
#         manifest={"key": "val"},
#         workflows={"wf1": ["list", "of", "modules"]},
#         paths={"input": "path1", "output": "path2"},
#         top_level_params={"one": 1, "two": 2},
#         module_keys={"key": "value1"},
#         module_registry_version="0.1.0",
#         module_sections={"another_key": "another_value"},
#         included_modules=["one", "two"],
#         inputs=["input1"],
#         outputs=["output1"],
#     )

#     repo = repository.ExperimentRepository(session)
#     repo.add(experiment)

#     contents = yaml.safe_load(())
#     # Want to write a test here that shows an experiment config (but eventually, the IO obj that corresponds to expconfig?) can be saved to disk.
