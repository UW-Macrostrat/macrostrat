import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Tuple

import fiona
import geopandas as G
import pandas as P
import pyogrio
from geoalchemy2 import Geometry
from rich.console import Console
from rich.progress import Progress
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from sqlalchemy import text

from macrostrat.map_integration.utils.gems_utils import (
    extract_gdb_layer,
    map_lines_to_preferred_fields,
    map_points_to_preferred_fields,
    map_strat_name,
    map_t_b_intervals,
    transform_gdb_layer,
)

from ..database import get_database
from ..errors import IngestError
from ..utils.ingestion_utils import map_t_b_standard
from .geodatabase import apply_domains_to_fields, get_layer_info, get_layer_names

console = Console()


def merge_metadata_polygons(polygon_df, meta_df, join_col) -> G.GeoDataFrame:
    # merge df (polygon df) and legend_df (created df from file)
    # ensure join column is string for both DataFrames
    polygon_df[join_col] = polygon_df[join_col].astype(str)
    meta_df[join_col] = meta_df[join_col].astype(str)
    # merge metadata into geodataframe
    merged_df = polygon_df.merge(
        meta_df, on=join_col, how="left", suffixes=("", "_meta")
    )
    # Drop duplicate columns (after merge)
    return merged_df


def preprocess_dataframe(
    poly_line_pt_df: G.GeoDataFrame, meta_path: Path, join_col: str, feature_suffix: str, pipeline: str
) -> Tuple[G.GeoDataFrame, str, str, str]:
    """
    Preprocess a GeoDataFrame by merging in metadata from a local .tsv,
    .csv, .xls, or .xlsx file.
    Parameters:
        poly_line_pt_df (G.GeoDataFrame): The geospatial dataframe to preprocess.
        meta_path (Path): Path to the legend.tsv metadata file.
        join_col (str): The column to join on (default is "mapunit").
    Returns:
        G.GeoDataFrame: The enriched GeoDataFrame with merged metadata.
    """
    # extract and store metadata into meta_df for processing.
    meta_df = None
    ingest_pipeline = ""
    comments = ""
    state = ""
    if pipeline == ".tsv":
        meta_df = P.read_csv(meta_path, sep="\t")
        ingest_pipeline = ".tsv pipeline"
        # TODO tsv pipeline for if feature_suffix == "polygons", "lines" OR "points"
    elif pipeline == ".csv":
        meta_df = P.read_csv(meta_path)
        ingest_pipeline = ".csv pipeline"
        # TODO csv pipeline for if feature_suffix == "polygons", "lines" OR "points"
    elif pipeline in [".xls", ".xlsx"]:
        ingest_pipeline = ".xls pipeline"
        meta_df = P.read_excel(meta_path)
        # TODO xls pipeline for if feature_suffix == "polygons", "lines" OR "points"
    elif pipeline == ".gpkg":
        meta_df = map_t_b_standard(poly_line_pt_df, "epoch", "period")
        ingest_pipeline = ".gpkg pipeline"
        state = "needs review"
        comments = ""
        return meta_df, ingest_pipeline, comments, state
    elif pipeline == ".gdb":
        if feature_suffix == "polygons":
            join_col = "mapunit"
            if join_col not in poly_line_pt_df.columns:
                comments = f"Warning: join column '{join_col}' not found in metadata file. Skipping metadata merge"
                state = "failed"
                return poly_line_pt_df, ingest_pipeline, comments, state
            meta_df, ingest_pipeline, comments = extract_gdb_layer(
                meta_path, "DescriptionOfMapUnits", False
            )
            # no gems metadata...continue ingesting other layers.
            if ingest_pipeline == ".gdb pipeline":
                return poly_line_pt_df, ingest_pipeline, comments, state
            if ingest_pipeline == "Gems pipeline" and comments != "":
                state = "failed"
                return poly_line_pt_df, ingest_pipeline, comments, state
            meta_df, comments = transform_gdb_layer(meta_df)
            if comments != "":
                # TODO update to needs review. this status makes UI fail for some reason so kept it at pending.
                state = "pending"
                return poly_line_pt_df, ingest_pipeline, comments, state
            meta_df = map_t_b_intervals(meta_df)
            if (
                meta_df["b_interval"].isna().all()
                and meta_df["t_interval"].isna().all()
            ):
                comments += "Both b_interval and t_interval are NA. "
                state = "failed"
                return poly_line_pt_df, ingest_pipeline, comments, state
            meta_df = map_strat_name(meta_df)
            if meta_df["strat_name"].isna().all():
                comments += "No strat_names found."
        elif feature_suffix == "lines":
            meta_df, comments, state = map_lines_to_preferred_fields(
                poly_line_pt_df, comments, state
            )
            if len(meta_df) == 0 or meta_df.empty:
                state = "failed"
                comments = "No lines to ingest"
            if state != "pending":
                state = "ingested"
                comments = " Lines successfully ingested"
            print("Lines df merge successful")
            return meta_df, ingest_pipeline, comments, state

        elif feature_suffix == "points":
            meta_df, comments, state = map_points_to_preferred_fields(
                poly_line_pt_df, comments, state
            )
            if len(meta_df) == 0 or meta_df.empty:
                state = "failed"
                comments = "No points to ingest"
            if state != "pending":
                state = "ingested"
                comments = " Points successfully ingested"
            print("Points df merge successful")
            return meta_df, ingest_pipeline, comments, state
    if meta_df is None:
        comments += "No metadata dataframe produced. Skipping metadata merge. "
        state = state or "needs review"
        return poly_line_pt_df, ingest_pipeline, comments, state

    if len(meta_df) == 0:
        comments += "Metadata dataframe is empty. Skipping metadata merge. "
        state = state or "needs review"
        return poly_line_pt_df, ingest_pipeline, comments, state

    # merge polygons and metadata dataframes before inserting into the db

    merged_df = merge_metadata_polygons(poly_line_pt_df, meta_df, join_col)
    print("Polygon df merge successful")

    comments += "Polygons metadata merged and ingested"
    state = "ingested"
    return merged_df, ingest_pipeline, comments, state


def strip_z(g: BaseGeometry | None):
    """Return a 2-D copy of *g* (or None)."""
    if g is None or g.is_empty or not g.has_z:
        return g  # already 2D / empty / null
    return wkt.loads(wkt.dumps(g, output_dimension=2))


def ingest_map(
    slug: str,
    files: List[Path],
    embed: bool = False,
    crs: str = None,
    pipeline: str = "",
    if_exists: str = "replace",
    meta_path: str = None,
    # TODO add default key column to the first column in the file
    merge_key: str = None,
    meta_table: str = "polygons",
    chunksize: int = 100,
) -> Tuple[str, str, str]:
    """Ingest general GIS data formatted_filenames into the database.

    This is similar to the macrostrat maps pipeline ingest-map command,
    but it doesn't upload formatted_filenames to S3 or check their existence.
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

    if meta_path:
        meta_path = Path(meta_path)
        join_col = merge_key
    else:
        meta_path = None
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
        except IngestError as e:
            continue
        finally:
            total_count += 1

    if success_count == 0:
        raise IngestError("No formatted_filenames successfully ingested")

    console.print(f"Successfully ingested {success_count} of {total_count} layers.")

    if embed:
        IPython.embed()
    ingest_results = {
        "ingest_pipeline": None,
        "comments": "",
        "state": None,
        "polygon_state": None,
        "line_state": None,
        "point_state": None,
    }
    # concatenate all polygons into a single df, lines, and points as well
    for feature_type, df_list in frames.items():
        # Concatenate all dataframes
        df = G.GeoDataFrame(P.concat(df_list, ignore_index=True))
        df = df.loc[:, ~df.columns.duplicated()]
        feature_suffix = feature_type.lower() + "s"
        if feature_suffix == "linestrings":
            feature_suffix = "lines"
        # preprocess dataframe will take the concatenated polygons, lines, or points df and see if there are any metadata
        # formatted_filenames to append and map based on whatever integration pipeline is needed (inferred from the meta_path's ext)
        if meta_path:
            df.columns = df.columns.str.lower()
            if pipeline == "":
                pipeline = meta_path.suffix.lower()
            df, ingest_pipeline, comments, state = preprocess_dataframe(
                df,
                meta_path=meta_path,
                join_col=join_col.lower(),
                feature_suffix=feature_suffix,
                pipeline=pipeline
            )
            if feature_suffix == "polygons":
                ingest_results["ingest_pipeline"] = ingest_pipeline
                ingest_results["polygon_state"] = json.dumps(
                    {
                        "status": state,
                        "pipeline": ingest_pipeline,
                        "feature_count": len(df),
                        "comments": comments,
                    }
                )
            if feature_suffix == "lines":
                ingest_results["line_state"] = json.dumps(
                    {
                        "status": state,
                        "pipeline": ingest_results["ingest_pipeline"],
                        "feature_count": len(df),
                        "comments": comments,
                    }
                )
            if feature_suffix == "points":
                ingest_results["point_state"] = json.dumps(
                    {
                        "status": state,
                        "pipeline": ingest_results["ingest_pipeline"],
                        "feature_count": len(df),
                        "comments": comments,
                    }
                )
            if len(comments) > 0:
                if ingest_results["comments"]:
                    ingest_results["comments"] += "; " + comments
                else:
                    ingest_results["comments"] = comments

            if state == "ingested" and ingest_results["state"] is None:
                ingest_results["state"] = "ingested"
            if state == "needs review" and ingest_results["state"] is None:
                ingest_results["state"] = "needs review"
            elif ingest_results["state"] is None:
                ingest_results["state"] = "pending"
            print("all required logs are updated.")
            before = df.columns.tolist()
            df = df.loc[:, ~df.columns.duplicated()]  # <- fix: reassign to merged_df!
            after = df.columns.tolist()
            removed = set(before) - set(after)
            if removed:
                console.print(
                    f"[yellow]Dropped duplicate columns after merge: {removed}"
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

            df["geometry"] = df["geometry"].apply(strip_z)
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
    return ingest_results


def create_dataframe_for_layer(file: Path, layer: str) -> G.GeoDataFrame:
    return G.read_file(file, layer=layer)


def get_dataframes(files) -> Iterable[Tuple[str, G.GeoDataFrame]]:
    single_file = len(files) == 1
    # ignore cross section polygons/lines/faults in Arizona CSAMapUnitPolys formatted_filenames.
    ignore_cs_prefix = (
        "CSA",
        "CSB",
        "CSC",
        "CSD",
        "CSE",
        "CSF",
        "CSG",
        "CSH",
        "CSI",
        "CMU",
    )
    ignore_cs_suffix = ("ContactsAndFaults", "MapUnitPolys", "OrientationPoints")
    ignore_misc = (
        "T_1_DirtyAreas",
        "T_1_LineErrors",
        "T_1_PointErrors",
        "T_1_PolyErrors",
    )
    for file in files:
        console.print(file, style="bold cyan")

        layers = get_layer_names(file)

        n_layers = len(layers)
        if n_layers > 1:
            console.print(f"{n_layers} layers.")

        for layer in layers:
            # ignore cross section polygons/lines/faults in Arizona CSAMapUnitPolys formatted_filenames.
            # skip if it's a misc layer
            if layer.startswith(ignore_misc):
                console.print(f"Skipping misc {layer}.")
                continue
            # skip if it's BOTH a cross section filename_prefix AND ends with a cross section suffix
            if layer.startswith(ignore_cs_prefix) and layer.endswith(ignore_cs_suffix):
                console.print(f"Skipping cross section {layer}.")
                continue

            name = get_layer_name(
                file, layer, single_file=single_file, single_layer=n_layers == 1
            )
            stmt = f"Layer [cyan]{layer}[/cyan]"
            if name != layer:
                stmt += f" -> [cyan]{name}[/cyan]"
            console.print(stmt)
            # Create the basic data frame
            df = G.read_file(file, layer=layer)
            df.columns = df.columns.str.replace(r"\s+", " ", regex=True).str.strip()

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
