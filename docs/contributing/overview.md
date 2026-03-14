# Contributing

There are two main ways to contribute to `facts-experiment-builder`. Most contributors will fall into the first category.

---

## I want to add or update a module

Module configurations live as YAML files in this repo. You don't need to understand the experiment builder codebase to add one — you just need to know your module's container image, arguments, inputs, and outputs.

**→ [Adding a Module](adding-a-module.md)**

---

## I want to modify the experiment builder itself

This covers changes to the CLI, application logic, adapters, or core domain (e.g. adding a new execution backend, changing how metadata is written, fixing a bug in path resolution).

Start with the architecture overview to understand the layered design, then use the command flow diagrams to trace exactly what runs for each CLI command.

**→ [Architecture](../reference/architecture.md)**

**→ [Command Flow](../reference/command_flow.md)**

### Dev setup

```shell
git clone https://github.com/fact-sealevel/facts-experiment-builder.git
cd facts-experiment-builder
uv sync
```

**Run tests:**
```shell
uv run pytest
```

**Lint and format:**
```shell
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```
