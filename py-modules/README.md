# Shared Python libraries

This directory includes shared Python modules that can be used across different services.
Simple modules can be placed here as an intermediate step before being moved to the
[`UW-Macrostrat/python-libraries`](https://github.com/UW-Macrostrat/python-libraries) repository.

These modules must be built before services can be compiled to Docker images.
The `scripts/build-image` command takes care of both steps together.
This is very much a work in progress.
