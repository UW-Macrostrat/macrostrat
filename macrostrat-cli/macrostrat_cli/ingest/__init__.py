from typer import Typer, Argument, echo
from typing import List
from pathlib import Path
import geopandas as G
import pandas as P
import IPython
from collections import defaultdict
from sqlalchemy import create_engine

from rich.console import Console

console = Console()
app = Typer()

# Database connection
engine = create_engine("postgresql://postgres:moovitbro@localhost:54381/burwell")


@app.command(name="ingest")
def ingest_map(
    source_id: str,
    files: List[Path],
    embed: bool = False,
    crs: str = None,
    if_exists: str = "replace",
):
    console.print("[bold]Ingesting map data for source [bold blue]" + source_id)
    # Read file with GeoPandas and dump to PostGIS

    frames = defaultdict(list)

    for file in files:
        df = G.read_file(file)

        console.print(file, style="bold cyan")

        # Print geometry type statistics
        counts = df.geometry.type.value_counts()
        for geom_type, count in counts.items():
            echo(f"- {count} {geom_type}s")

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
            echo(f"- {col}")

        table = f"{source_id}_{feature_type.lower()}s"
        schema = "map_staging"

        console.print(f"Writing {feature_type}s to [cyan]{schema}.{table}")
        engine.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        # Get first 10 rows

        df.to_postgis(
            table,
            engine,
            if_exists=if_exists,
            schema=schema,
            chunksize=100,
        )
