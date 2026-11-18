"""Load geospatial files into the database, inferring a table structure.

The geospatial counterpart to [cyan]load-csv[/], with the same semantics: the
destination table is created to match the file, named after it, and placed in
the [cyan]temp[/] schema by default. The work is done by
[cyan]macrostrat.loader_utils.load_layer[/].
"""

from pathlib import Path
from sys import stderr
from typing import Optional

import typer
from rich import print
from typer import Argument, Option

from macrostrat.loader_utils import DEFAULT_SRID, LoadError, load_layer, render_ddl

from .utils import engine_for_db_name


def load_geo(
    files: list[Path] = Argument(..., help="Geospatial file(s) to load"),
    schema: str = Option("temp", "--schema", "-n", help="Schema to create tables in"),
    table: Optional[str] = Option(
        None,
        "--table",
        "-t",
        help="Table name (defaults to the file name). Only valid for a single layer.",
    ),
    layer: Optional[str] = Option(
        None,
        "--layer",
        "-l",
        help="Layer to load. Defaults to every layer in the file, each into its own table.",
    ),
    database: Optional[str] = Option(None, "--database", help="Database to connect to"),
    srid: Optional[int] = Option(
        None,
        "--srid",
        help=f"Target SRID to reproject to (default: {DEFAULT_SRID})",
    ),
    keep_srid: bool = Option(
        False,
        "--keep-srid",
        help="Keep the file's own CRS instead of reprojecting to EPSG:4326",
    ),
    source_srid: Optional[int] = Option(
        None,
        "--source-srid",
        help=(
            "Declare the source CRS for a file that has none (or override a wrong "
            "one). Reprojection to the target SRID still applies unless --keep-srid."
        ),
    ),
    geometry_column: str = Option(
        "geom", "--geometry-column", "-g", help="Name of the geometry column"
    ),
    fid_column: Optional[str] = Option(
        None,
        "--fid-column",
        help="Keep the layer's feature ID as an attribute column of this name",
    ),
    promote_to_multi: bool = Option(
        False,
        "--multi",
        help="Promote single geometries to their Multi* equivalent, so mixed layers share one type",
    ),
    no_index: bool = Option(
        False, "--no-index", help="Skip creating the GIST index on the geometry column"
    ),
    where: Optional[str] = Option(
        None, "--where", help="OGR attribute filter applied while reading"
    ),
    replace: bool = Option(
        False, "--replace", help="Drop and recreate the table if it already exists"
    ),
    append: bool = Option(
        False, "--append", help="Append to an existing table instead of creating it"
    ),
    dry_run: bool = Option(
        False,
        "--dry-run",
        help="Print the inferred table structure without touching the database",
    ),
):
    """Load geospatial files into the database, creating tables to match the data.

    The geospatial counterpart to [cyan]load-csv[/]. Reads anything GDAL/OGR can
    (Shapefile, GeoPackage, GeoJSON, FileGDB, …), creating one table per layer in
    the [cyan]temp[/] schema and reprojecting to EPSG:4326 by default.
    """
    from pyogrio import list_layers

    engine = engine_for_db_name(database)

    for file in files:
        if not file.exists():
            raise typer.BadParameter(f"File {file} does not exist")

        if layer is not None:
            layers = [layer]
        else:
            layers = [str(name) for name, _ in list_layers(file)]
            if not layers:
                raise typer.BadParameter(f"No layers found in {file}")

        if table is not None and (len(layers) > 1 or len(files) > 1):
            raise typer.BadParameter(
                "--table cannot be used with multiple files or layers; "
                "use --layer to pick one"
            )

        for name in layers:
            try:
                result = load_layer(
                    engine,
                    file,
                    name,
                    schema=schema,
                    table=table,
                    single_layer=len(layers) == 1,
                    srid=srid,
                    keep_srid=keep_srid,
                    source_srid=source_srid,
                    geometry_column=geometry_column,
                    fid_column=fid_column,
                    promote_to_multi=promote_to_multi,
                    index=not no_index,
                    where=where,
                    replace=replace,
                    append=append,
                    dry_run=dry_run,
                )
            except LoadError as err:
                raise typer.BadParameter(str(err)) from err

            if dry_run:
                print(
                    render_ddl(
                        engine,
                        result.schema,
                        result.table,
                        result.columns,
                        result.types,
                    )
                )
                continue

            geometry = "no geometry"
            if result.geometry_type is not None:
                geometry = f"{result.geometry_type} @ {result.srid}"
            print(
                f"[dim]Loaded[/] [bold cyan]{file}[/][dim]:[/][cyan]{name}[/] [dim]→[/] "
                f"[bold green]{result.schema}.{result.table}[/] "
                f"[dim]({result.copied} features, {geometry})[/]",
                file=stderr,
            )
