from typing import List
from pathlib import Path
import geopandas as G
import pandas as P
import IPython
from collections import defaultdict
from sqlalchemy import create_engine
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import *

from geopandas.io.sql import _get_geometry_type, _convert_to_ewkb, _psql_insert_copy

from rich.console import Console
from rich.progress import Progress

from ..database import db

console = Console()


def ingest_map(
    source_id: str,
    files: List[Path],
    embed: bool = False,
    crs: str = None,
    if_exists: str = "replace",
):
    """Ingest shapefiles into the database."""
    console.print("[bold]Ingesting map data for source [bold blue]" + source_id)
    # Read file with GeoPandas and dump to PostGIS

    frames = defaultdict(list)

    for file in files:
        df = G.read_file(file)

        console.print(file, style="bold cyan")

        # Print geometry type statistics
        counts = df.geometry.type.value_counts()
        for geom_type, count in counts.items():
            console.print(f"- {count} {geom_type}s")

        if crs is not None:
            if df.crs is None:
                console.print("Forcing input CRS to [bold yellow]" + crs)
                df.crs = crs
            else:
                raise ValueError("CRS already set")

        # If no CRS is set, demand one.
        if df.crs is None:
            console.print(
                "No CRS set. Please set a CRS before ingesting.", style="bold red"
            )
            return

        # Convert geometry to WGS84
        console.print("Projecting to WGS84")
        df = df.to_crs("EPSG:4326")

        # Add file name to dataframe
        df["source_layer"] = file.stem

        # Concatenate to polygons
        for feature_type in ("Polygon", "LineString", "Point"):
            frames[feature_type].append(df[df.geometry.type == feature_type])
            frames[feature_type].append(df[df.geometry.type == "Multi" + feature_type])

        console.print()

    if embed:
        IPython.embed()

    for feature_type, df_list in frames.items():
        # Concatenate all dataframes
        df = G.GeoDataFrame(P.concat(df_list, ignore_index=True)).dropna(
            axis=1, how="all"
        )

        console.print(f"[bold]{feature_type}s[/bold] [dim]- {len(df)} features[/dim]")
        # Columns
        console.print("Columns:")
        for col in df.columns:
            console.print(f"- {col}")

        table = f"{source_id}_{feature_type.lower()}s"
        schema = "sources"
        chunksize = 10

        db.engine.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        console.print(f"Writing [blue dim]{schema}.{table}")
        # Get first 10 rows

        # Iterate through chunks and write to PostGIS
        with Progress() as progress:
            task = progress.add_task(
                f"Writing {feature_type}s",
                total=len(df),
            )

            geom_name = df.geometry.name
            geometry_type, has_curve = _get_geometry_type(df)
            df = _convert_to_ewkb(df, geom_name, 4326)

            for i, chunk in enumerate(chunker(df, chunksize)):
                chunk.to_sql(
                    table,
                    db.engine,
                    schema=schema,
                    if_exists=if_exists if i == 0 else "append",
                    dtype={geom_name: Geometry(geometry_type=geometry_type, srid=4326)},
                    method=_psql_insert_copy,
                )
                progress.update(task, advance=len(chunk))


def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
