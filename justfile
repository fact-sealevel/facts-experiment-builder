# format python files
format:
	uv run ruff format

# format docstrings
format-docs:
	uv run docformatter --in-place --recursive \
		--wrap-summaries 88 --wrap-descriptions 88 src/ || [ $? -eq 3 ]
# lint python files, fixing what can be fixed
lint:
	uv run ruff check --fix

# run tests
test:
	uv run pytest \
	--ignore=tests/unit/test_experiment_repository.py \
	-v --color=yes

# run tests with coverage
test-cov:
	uv run pytest \
	--ignore=tests/unit/test_experiment_repository.py \
	-vv --color=yes --cov=src

# run format, linting, testing checks
validate: format format-docs lint test-cov