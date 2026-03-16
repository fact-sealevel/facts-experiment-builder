# Installation

## Run without installing (recommended for users)

Use `uvx` to run `facts-experiment-builder` directly from GitHub without installing it:

```shell
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main setup-new-experiment --help
uvx --from git+https://github.com/fact-sealevel/facts-experiment-builder@main generate-compose --help
```

## Development setup

Clone the repo and install with [uv](https://docs.astral.sh/uv/):

```shell
git clone https://github.com/fact-sealevel/facts-experiment-builder.git
cd facts-experiment-builder
uv sync
```

This installs the package in editable mode along with all dev dependencies. CLI commands are then available via:

```shell
uv run setup-new-experiment --help
uv run generate-compose --help
```

### Install docs dependencies

```shell
uv sync --group docs
uv run mkdocs serve   # preview docs locally at http://127.0.0.1:8000
```

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker (to actually run generated compose files)
