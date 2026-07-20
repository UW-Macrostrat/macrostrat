# Macrostrat

A geological data platform for exploration, integration, and analysis (v2).

This repository represents the core of the Macrostrat system, containing its
database schema and control scripts to maintain it. As such, it provides a
"build recipe" for the open-source core of Macrostrat, which in **v2** will be
provided publicly as a runnable platform for curating geologic maps and other
datasets.

The core component packaged here is a Python application designed to control
various aspects of Macrostrat's system and supporting processes (e.g., map
caching and harmonization).

## Key components in this repository

### Management utilities

- [Command-line interface](./cli): A Python-based CLI for managing Macrostrat's
  system components
- [Map ingestion system](./map-integration): Scripts for importing geologic maps
  into Macrostrat's database

### Services

Macrostrat's core services are housed in the `services/` directory:

- [API v3](./services/api-v3): An API for managing Macrostrat elements, and authentication
- Macrostrat task runner: *coming soon*

Other Macrostrat services (e.g., read-only APIs) are housed in other repositories.

## Installation

The project is built using `uv`. It is required to have `uv` installed on your system.
UV can be installed directly [instructions here](https://uv.readthedocs.io/en/latest/installation.html).
Alternatively, we recommend `mise` to manage UV and Python versions.

Some services (notably the legacy tileserver) use older versions of Python or other languages entirely.

- Running `make` will install the Python dependencies and build the application.
- `make test` will run the test suite.
- `make install` will install the application into the local root.

Setting the `MACROSTRAT_PYROOT` environment variable allows a different root
Python version to be installed. This can be used to add new plugins
or application dependencies.

### Debugging the installation

- Run `macrostrat uv sync` to ensure that all dependencies are installed.

## Usage

Once a Macrostrat configuration file is defined, the Macrostrat command-line app
presents a broad list of management functionality for Macrostrat's system. **Subsystems**
(*in progress*) define functionality for specific aspects of the system.

This CLI is rapidly evolving so expect breakage! When in doubt run `make`, or ~equivalently
`uv sync` to update your installation.

## Testing

The `macrostrat test` command is a thin wrapper around `pytest`.
The `all` subcommand forwards extra arguments directly to `pytest`, so you can
mix standard pytest flags (`-x`, `-k`, `-m`, etc.) with Macrostrat-specific options
defined in `conftest.py`.

### Test modes

- **Environment/conformance tests** use the `env_config`, `env_db`, and `db` fixtures.
  They target a configured Macrostrat environment from your `macrostrat.toml`.
- **Clean-room database tests** use `empty_db` and `test_db`.
  They create a temporary PostgreSQL cluster, apply schema, and run tests against it.
- **Unit-style tests** do not require either database fixture.

### Macrostrat-specific pytest options

- `--skip-env`: skip environment-backed tests that require `env_config`/`env_db`/`db`. This is the default
  for CI runs.
- `--env ENV`: override the active Macrostrat environment for the test run.
- `--skip-database`: skip creation of the temporary clean-room database.
- `--skip-slow`: skip tests marked `@pytest.mark.slow`.
- `--optimize-database`: (on by default) enable faster schema setup for clean-room tests by skipping
  non-essential statements (indexes, grants, and ownership changes).

### Fixture behaviors

- `env_db` connects to the database for the active environment, then sets `ROLE web_anon` to ensure that tests are read-only.
- `db` wraps each test class in a transaction and rolls it back. Environment-backed tests should
  not change the database so this is purely a precautionary measure.
- `test_db` applies schema for the current environment. with transactional rollback as well.

### Common commands

```bash
# Full suite (environment + clean-room + unit tests)
macrostrat test all

# Local/CI-friendly run without environment-backed tests (same intent as `make test`)
macrostrat test all --skip-env -x -s

# Focus on fast tests only
macrostrat test all --skip-env --skip-database --skip-slow

# Target a specific environment for conformance tests
macrostrat test all --env development
```

For marker-based filtering, the repository also defines `docker` and `requires_gdal`
pytest markers in `pyproject.toml`.



## Documentation

Documentation is a work in progress. We have starting points for:

* [Macrostrat's system architecture](docs/Macrostrat%20System%20Architecture.md)

* [Macrostrat in a Box](docs/Macrostrat%20in%20a%20Box.md), a future Docker
  Compose-based setup for running Macrostrat locally on a single host

* [The `macrostrat` command line app](cli/docs/cli-usage.md)

* [Map staging scripts](map-staging/README.md): ad-hoc scripts for scraping
  vector maps from the web and uploading to Macrostrat

Other documentation of general interest can be found in the [docs/](docs/)
directory.

