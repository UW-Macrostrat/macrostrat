# Macrostrat command-line interface

The Macrostrat command-line interface is a tool for orchestrating and managing
the Macrostrat platform, including its database(s) and services. It is designed
both to bootstrap and control an standalone Macrostrat installation, and to help
control the infrastructure of the entire Macrostrat project, which contains
multiple databases for developement and differently-targeted collaborations.

This module, formerly known as _utils_, contains the central command-line
application for orchestrating and managing the Macrostrat system.

## Installation

- Install a recent version of `python3` and `poetry`
- `make` (runs `poetry install`)
- `make install` (links the application into `/usr/local/bin`)
- Optionally, install subsystems for additional functionality (coming soon)

## Configuration

The CLI is configured using [Dynaconf](https://www.dynaconf.com/), which allows
for a variety of configuration sources, including environment variables, YAML
files, and TOML files. The most flexible way to configure the CLI is using a
TOML file; an example is provide in
[`macrostrat-config.example.toml`](../macrostrat-config.example.toml).

## Usage

See [the CLI docs](docs/cli-usage.md) for CLI functionality

## Legacy

The basis of the Macrostrat CLI is in Python scripts in the
[`utils` repository](https://github.com/UW-Macrostrat/utils) that were used to
control the Macrostrat map system starting in 2015, when **v1** of Macrostrat's
map system was created. These scripts were used to manage the map system's
database on a single server.

As Macrostrat has transitioned to a more distributed set of containerized
services, and less centralized workflows, the tight focus of the original CLI
has become an difficult fit in our ecosystem. By making the tool pluggable and
aware of different Macrostrat environments, we hope a renewed Macrostrat CLI can
supply some broad organization to the platform's second act.

## Architecture

The Macrostrat CLI is a Python 3 package that can manage a containerized set of
Macrostrat services, orchestrated in either Docker Compose or Kubernetes. The
CLI is designed to be extensible, both to

- Manage different Macrostrat environments, such as development, staging, and
  production, and pass data between them
- Manage Macrostrat services, including applications that are not part of every
  Macrostrat installation (e.g., Paleogeography, Rockd, etc.)

Most components of Macrostrat rely on specific capabilities and datasets within
Macrostrat's core PostGIS database. Thus, the main focus of this tool is to
shape and maintain the database and the data it contains. It also includes
scripts for service inspection, deployment, orchestration, and other management
utilities.

**v2** of this system is in early development, and its management tools are both
incomplete and relatively poorly tested. Many capabilities will be implemented
within
[Macrostrat's shared Python libraries](https://github.com/UW-Macrostrat/python-libraries),
which will be used for other Macrostrat applications, such as
[Sparrow](https://github.com/EarthCubeGeochron/Sparrow).
