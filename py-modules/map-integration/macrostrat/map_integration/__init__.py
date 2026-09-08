"""Macrostrat's map-integration tools.

Deliberately empty. The Typer app lives in `.cli`, so importing a module from
this package -- `source_tables`, `process.geometry`, `utils.map_info` -- does not
drag in the whole command layer and everything it depends on. That mattered as
soon as something outside this monorepo tried to use one: a pipeline in its own
virtualenv, a notebook, a test.

Import the CLI explicitly:

    from macrostrat.map_integration.cli import cli
"""
