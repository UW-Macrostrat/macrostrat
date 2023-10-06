# Macrostrat CLI

This module, formerly known as _utils_, contains the central
command-line application for orchestrating and managing the Macrostrat
system. It includes scripts for service inspection, data maintenance,
and other management utilities.

## Installation

- Install a recent version of `python3` and `poetry`
- `make` (runs `poetry install`)
- `make install` (links the application into `/usr/local/bin`)
- Optionally, install subsystems for additional functionality (coming soon)

## Legacy code

The `utils` module that forms the core of this codebase was devised to manage
the Macrostrat v1 system on a single server. This code is still available
on the `v1` branch of this repository. 
