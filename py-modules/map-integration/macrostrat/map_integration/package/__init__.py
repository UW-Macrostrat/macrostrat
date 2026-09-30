"""Macrostrat map packages: moving compiled maps between environments.

A package is a GeoPackage holding one or more maps with everything that
describes them -- the `maps.sources` record, features, legend, `sources.*`
staging tables, ingest process, bounds and compilation membership -- keyed by
slug so it can be loaded into any Macrostrat database.

    macrostrat maps export ngs.gpkg --compilation ngs
    macrostrat maps ingest ngs.gpkg

See `docs/Map packages.md` for the format and what an import does.
"""

from importlib import import_module

# Resolved lazily so registering the CLI doesn't import pandas and GDAL
_exports = {
    "FORMAT_NAME": "format",
    "FORMAT_VERSION": "format",
    "is_map_package": "format",
    "read_package": "format",
    "export_maps": "export",
    "compilation_tree": "export",
    "ConflictAction": "load",
    "ImportReport": "load",
    "ImportStopped": "load",
    "import_package": "load",
}


def __getattr__(name):
    if name in _exports:
        return getattr(import_module(f".{_exports[name]}", __name__), name)
    raise AttributeError(name)
