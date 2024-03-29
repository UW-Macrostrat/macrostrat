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

## Installation

The Macrostrat _v2_ codebase requires `docker`, and either `docker compose` or
`kubectl` (for Kubernetes) to run.

To install the Python application that controls Macrostrat, head to the
[py-root](py-root) directory. Running `make` will install the Python
dependencies and build the application.

## Documentation

Documentation is a work in progress. We have starting points for:

* [Macrostrat's system architecture](docs/Macrostrat%20System%20Architecture.md)

* [Macrostrat in a Box](docs/Macrostrat%20in%20a%20Box.md), a future Docker
  Compose-based setup for running Macrostrat locally on a single host

* [The `macrostrat` command line app](cli/docs/cli-usage.md)

Other documentation of general interest can be found in the [docs/](docs/)
directory.
