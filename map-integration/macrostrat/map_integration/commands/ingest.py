import os
from collections import defaultdict
from optparse import Option
from pathlib import Path
from typing import Iterable, List, Tuple

import fiona
import geopandas as G
import pandas as P
import pyogrio
from geoalchemy2 import Geometry
from numpy.f2py.symbolic import as_ge
from pandas import DataFrame
from rich.console import Console
from rich.progress import Progress
from sqlalchemy import text

from ..custom_integrations.gems_utils import (
    extract_gdb_layer,
    map_strat_name,
    map_t_b_intervals,
    transform_gdb_layer,
)
from ..database import get_database
from ..errors import IngestError
from .geodatabase import apply_domains_to_fields, get_layer_info, get_layer_names

console = Console()


def merge_metadata_polygons(polygon_df, legend_df, join_col):
    # merge df (polygon df) and legend_df (created df from file)
    # ensure join column is string for both DataFrames
    polygon_df[join_col] = polygon_df[join_col].astype(str)
    legend_df[join_col] = legend_df[join_col].astype(str)
    # merge metadata into geodataframe
    merged_df = polygon_df.merge(legend_df, on=join_col, how="left")
    return merged_df


def preprocess_dataframe(
    df: G.GeoDataFrame, legend_path: Path, join_col: str
) -> G.GeoDataFrame:
    """
    Preprocess a GeoDataFrame by merging in metadata from a local .tsv,
    .csv, .xls, or .xlsx file.
    Parameters:
        df (G.GeoDataFrame): The geospatial dataframe to preprocess.
        legend_path (Path): Path to the legend.tsv metadata file.
        join_col (str): The column to join on (default is "symbol").
    Returns:
        G.GeoDataFrame: The enriched GeoDataFrame with merged metadata.
    """
    # extract and store metadata into legend_df for processing.
    legend_df = None
    ext = legend_path.suffix.lower()
    if ext == ".tsv":
        legend_df = P.read_csv(legend_path, sep="\t")
    elif ext == ".csv":
        legend_df = P.read_csv(legend_path)
    elif ext in [".xls", ".xlsx"]:
        legend_df = P.read_excel(legend_path)
    # note that the gdb dir may not contain shp files to merge metadata into
    # TODO add lines metadata ingestion hereeee
    # TODO ensure this is a gems dataset (list all layers) OR .gdb
    elif ext == ".gdb":

        # extract whatever layer you want to merge with the polygons table
        print("\n\nPolygons df before any metadata processing\n", df.columns.tolist())
        print("", df.head(5).T)

        legend_df = extract_gdb_layer(legend_path, "DescriptionOfMapUnits", False)

        print("\n\nDMU df before transform\n", legend_df.columns.tolist())
        print("", legend_df.head(5).T)
        # transform the standard gems columns to macrostrat columns
        # delete all of the arizona maps that are empty
        # create delete bulk ingestion script
        # what other info to add into ingest process table. recored type of ETL operations are performed in ingest table.
        # can remove ingest_process table if we don't need.
        # how to flag maps if pre process is ready (in the ui) for daven to post process.
        # celery process to have a delete button in the UI.
        # post UI manual column input json into the db for column ingestion...need RLS for user to post correct data to.
        # infrastructure....
        # suite of tests to run for rls to show what edge cases work. point to dev postgrest RLS
        # run role migration to ensure that the roles
        # once rls works have david update the UI immediately!
        # streamline the api's and UI for production.

        legend_df = transform_gdb_layer(legend_df)

        print("\n\nAFTER TRANSFORMATION!!\n\n")
        print("\n\nPolygons df\n", df.columns.tolist())
        print("\n\nDMU df\n", legend_df.columns.tolist())

        legend_df = map_t_b_intervals(legend_df)
        legend_df = map_strat_name(legend_df)

    if join_col not in df.columns:
        console.print(
            f"[yellow]Warning: join column '{join_col}' not found in legend file. Skipping merge.[/yellow]"
        )
        return df
    # merge polygons and metadata dataframes before inserting into the db
    merged_df = merge_metadata_polygons(df, legend_df, join_col)
    return merged_df


def ingest_map(
    slug: str,
    files: List[Path],
    embed: bool = False,
    crs: str = None,
    if_exists: str = "replace",
    legend_file: str = None,
    # TODO add default key column to the first column in the file
    legend_key: str = None,
    legend_table: str = "polygons",
    chunksize: int = 100,
):
    """Ingest general GIS data files into the database.

    This is similar to the macrostrat maps pipeline ingest-map command,
    but it doesn't upload files to S3 or check their existence.
    """
    db = get_database()

    console.print("[bold]Ingesting map data for source [bold blue]" + slug)
    # Read file with GeoPandas and dump to PostGIS

    # We need to put multigeometries first, otherwise they might not be used in the
    frames = defaultdict(list)

    # Add to map-sources table
    db.run_sql(
        f"INSERT INTO maps.sources (primary_table, slug) VALUES ('{slug}_polygons', '{slug}') ON CONFLICT DO NOTHING"
    )

    success_count = 0
    total_count = 0

    if legend_file:
        legend_path = Path(legend_file)
        join_col = legend_key
    else:
        legend_path = None
        join_col = None

    for name, df in get_dataframes(files):
        try:

            if crs is not None:
                if df.crs is None:
                    console.print("Forcing input CRS to [bold yellow]" + crs)
                    df.crs = crs
                else:
                    raise IngestError("CRS already set")

            # If no CRS is set, demand one.
            if df.crs is None:
                console.print(
                    "No CRS set. Please set a CRS before ingesting.", style="bold red"
                )
                raise IngestError("No CRS set")

            # Convert geometry to WGS84
            console.print("Projecting to WGS84")
            df = df.to_crs("EPSG:4326")

            # Add file name to dataframe
            df["source_layer"] = name

            # Remove the second instance of any repeated column
            _dup = df.columns.duplicated()
            # Print warning
            for column in df.columns[_dup]:
                console.print(
                    "[yellow dim]Ignoring duplicate column:[/yellow dim] [yellow]"
                    + column
                )

            df = df.loc[:, ~_dup]
            # Print warning

            # Concatenate to polygons
            for feature_type in ("Polygon", "LineString", "Point"):
                frames[feature_type].append(df[df.geometry.type == feature_type])
                frames[feature_type].append(
                    df[df.geometry.type == "Multi" + feature_type]
                )

            success_count += 1
            console.print()
        except IngestError as e:
            continue
        finally:
            total_count += 1

    if success_count == 0:
        raise IngestError("No files successfully ingested")

    console.print(f"Successfully ingested {success_count} of {total_count} layers.")

    if embed:
        IPython.embed()

    for feature_type, df_list in frames.items():
        # Concatenate all dataframes
        df = G.GeoDataFrame(P.concat(df_list, ignore_index=True)).dropna(
            axis=1, how="all"
        )

        feature_suffix = feature_type.lower() + "s"
        if feature_suffix == "linestrings":
            feature_suffix = "lines"

        # applies legend merge only to the whatever the legend_table is specified as
        if legend_path and legend_table == feature_suffix:
            df.columns = df.columns.str.lower()
            df = preprocess_dataframe(
                df, legend_path=legend_path, join_col=join_col.lower()
            )

        console.print(f"[bold]{feature_type}s[/bold] [dim]- {len(df)} features[/dim]")
        # Columns
        console.print("Columns:")
        for col in df.columns:
            console.print(f"- {col}")

        table = f"{slug}_{feature_suffix}"
        schema = "sources"

        db.run_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        console.print(f"Writing [blue dim]{schema}.{table}")
        # Get first 10 rows

        # Iterate through chunks and write to PostGIS
        with Progress() as progress:
            task = progress.add_task(
                f"Writing {feature_type}s",
                total=len(df),
            )

            conn = db.engine.connect()

            for i, chunk in enumerate(chunker(df, chunksize)):
                chunk.to_postgis(
                    table,
                    conn,
                    schema=schema,
                    if_exists=if_exists if i == 0 else "append",
                    dtype={
                        "geometry": Geometry(
                            geometry_type="Geometry",
                            spatial_index=True,
                            srid=4326,
                        ),
                    },
                )
                # Ensure multigeometries are used (brute force)
                if i == 0:
                    conn.execute(
                        text(
                            f"ALTER TABLE {schema}.{table} ALTER COLUMN geometry TYPE Geometry(Geometry, 4326)"
                        )
                    )
                progress.update(task, advance=len(chunk))

            conn.commit()


def create_dataframe_for_layer(file: Path, layer: str) -> G.GeoDataFrame:
    return G.read_file(file, layer=layer)


def get_dataframes(files) -> Iterable[Tuple[str, G.GeoDataFrame]]:
    single_file = len(files) == 1
    for file in files:
        console.print(file, style="bold cyan")

        layers = get_layer_names(file)

        n_layers = len(layers)
        if n_layers > 1:
            console.print(f"{n_layers} layers.")

        for layer in layers:
            name = get_layer_name(
                file, layer, single_file=single_file, single_layer=n_layers == 1
            )
            stmt = f"Layer [cyan]{layer}[/cyan]"
            if name != layer:
                stmt += f" -> [cyan]{name}[/cyan]"
            console.print(stmt)

            # Create the basic data frame
            df = G.read_file(file, layer=layer)

            info = get_layer_info(file, layer)
            # Apply domains for Geodatabase linked information
            df = apply_domains_to_fields(df, info)

            # TODO: find and follow foreign key relationships

            _print_layer_info(df, console)

            yield name, df


def _print_layer_info(df, _console: Console):

    # If there is no geometry, skip
    if "geometry" not in df.columns:
        _console.print("No geometry column found. Skipping.")
        return

    # Print geometry type statistics
    counts = df.geometry.type.value_counts()
    for geom_type, count in counts.items():
        _console.print(f"- {count} {geom_type}s")

    _col_list = ", ".join(df.columns)
    # Print out column names
    _console.print(f"- [bold]Columns[/bold]: [dim]{_col_list}[/dim]")


def get_layer_name(
    file: Path, layer: str, single_file=False, single_layer=False
) -> str:
    """Get the best layer name for a file and layer."""
    name = file.stem
    if single_layer:
        return name
    if single_file:
        return layer
    return f"_{layer}"


# infer age from column
# post process for all local maps as well as the national map.
# def post_process_dataframe(df: DataFrame, console: Console): rgb color, t-age, b-age,


def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
