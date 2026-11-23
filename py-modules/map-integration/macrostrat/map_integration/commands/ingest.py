import json
import re
from collections import defaultdict
from functools import cache
from pathlib import Path
from typing import Annotated, Iterable, List, Optional, Tuple

import geopandas as G
import pandas as P
from geoalchemy2 import Geometry
from rich.console import Console
from rich.progress import Progress
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from sqlalchemy import text
from typer import Argument, Option

from macrostrat.map_integration.utils.gems_utils import (
    extract_gdb_layer,
    map_legend_ages,
    map_lines_to_preferred_fields,
    map_points_to_preferred_fields,
    transform_gdb_layer,
)
from macrostrat.map_utils.slugs import check_slug, staging_table, table_prefix

from ..database import get_database
from ..errors import IngestError
from ..package.load import ConflictAction
from ..utils.ingestion_utils import map_t_b_standard
from .geodatabase import apply_domains_to_fields, get_layer_info, get_layer_names

console = Console()

#: What `--pipeline` accepts with a metadata path: `gems` reads the GeMS legend
#: from a .gdb or .gpkg, `.tsv`/`.csv`/`.xls`/`.xlsx` read a legend table,
#: `.gpkg` maps epoch/period columns to intervals, and `none` merges nothing.
PIPELINES = ("gems", ".tsv", ".csv", ".xls", ".xlsx", ".gpkg", "none")


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


#: A legend column kept beside the polygons' own under a name other than
#: `<column>_from_dmu`: the legend's `label` is the map's `unit_label`.
DMU_DUPLICATE_NAMES = {"label": "unit_label"}


def name_dmu_columns(polygon_df, merged_df) -> G.GeoDataFrame:
    """Name the GeMS legend (DescriptionOfMapUnits) columns the merge suffixed
    `_meta` because the polygons had a column of the same name.

    Where the polygons' column is empty, the legend's takes its name: `age`.
    Where it has values, the legend's is kept beside it as `<column>_from_dmu`
    (`age_from_dmu`), except `label`, which is `unit_label`. `transform_gdb_layer`
    has already copied the legend's label there, so the suffixed copy is dropped.
    """
    for column in [c for c in merged_df.columns if c.endswith("_meta")]:
        base = column.removesuffix("_meta")
        if base not in polygon_df:
            continue
        if _blank(polygon_df[base]).all():
            merged_df[base] = merged_df.pop(column)
        else:
            dmu = DMU_DUPLICATE_NAMES.get(base, f"{base}_from_dmu")
            if dmu in merged_df:
                merged_df = merged_df.drop(columns=column)
            else:
                merged_df = merged_df.rename(columns={column: dmu})
    return merged_df


def preprocess_dataframe(
    db,
    poly_line_pt_df: G.GeoDataFrame,
    meta_path: Path,
    join_col: str,
    feature_suffix: str,
    pipeline: str,
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
        ingest_pipeline = ".gpkg pipeline"
        state = "needs review"
        comments = ""
        if feature_suffix == "polygons":
            meta_df = map_t_b_standard(db, poly_line_pt_df, "epoch", "period")
            return meta_df, ingest_pipeline, comments, state
        else:
            return poly_line_pt_df, ingest_pipeline, comments, state

    elif pipeline == "gems":
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
            meta_df = map_legend_ages(db, meta_df)
            if (
                meta_df["b_interval"].isna().all()
                and meta_df["t_interval"].isna().all()
            ):
                comments += "Both b_interval and t_interval are NA. "
                state = "failed"
                return poly_line_pt_df, ingest_pipeline, comments, state
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
        comments = "No metadata in maps.sources."
        state = state or "needs review"
        return poly_line_pt_df, ingest_pipeline, comments, state

    if len(meta_df) == 0:
        comments += "Metadata dataframe is empty. Skipping metadata merge. "
        state = state or "needs review"
        return poly_line_pt_df, ingest_pipeline, comments, state

    # merge polygons and metadata dataframes before inserting into the db

    merged_df = merge_metadata_polygons(poly_line_pt_df, meta_df, join_col)
    if pipeline == "gems":
        merged_df = name_dmu_columns(poly_line_pt_df, merged_df)
    print("Polygon df merge successful")

    comments += "Polygons metadata merged and ingested"
    state = "ingested"
    return merged_df, ingest_pipeline, comments, state


@cache
def _strat_name_vocabulary(db):
    """Loaded once per process: `calculate-strat-name` runs this map by map."""
    from ..match.strat_names import prepare_ingest

    return prepare_ingest(db)


def _blank(series: P.Series) -> P.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def map_strat_name_ingest(db, df: P.DataFrame) -> P.DataFrame:
    """Fill `strat_name` with a best guess at the stratigraphic names each
    polygon's `name` gives, or its `descrip` (then `description`) where `name`
    gives none. Run on every ingested polygon layer, whatever `--pipeline`, and
    by `macrostrat maps staging normalize calculate-strat-name` once those
    fields have been curated.

    Names Macrostrat's lexicon carries come first, written as the lexicon writes
    them (`named_units`); failing those, names by their form alone
    (`formal_names`), such as `Belmont Granite`. A polygon whose text gives
    neither is left null rather than given its raw text, and a `strat_name` the
    data already has is kept.
    """
    from ..match.strat_names import formal_names, named_units

    columns = {c.lower(): c for c in df.columns}
    sources = [columns[c] for c in ("name", "descrip", "description") if c in columns]
    if not sources:
        return df

    lexicon, lexicon_names, vocabulary, ordinary = _strat_name_vocabulary(db)
    common = {
        word.lower()
        for column in sources
        for text in df[column].dropna().astype(str)
        for word in re.findall(r"[A-Za-z]+", text)
        if word[0].islower()
    }
    guesses = {}

    def guess(text: str):
        if text not in guesses:
            names = named_units(text, lexicon, lexicon_names) or formal_names(
                text, vocabulary, common, ordinary
            )
            guesses[text] = "; ".join(names) or None
        return guesses[text]

    # Each source in turn, for the rows the ones before it gave nothing.
    guessed = P.Series(None, index=df.index, dtype=object)
    for column in sources:
        texts = df[column].mask(_blank(df[column]))
        todo = guessed.isna() & texts.notna()
        guessed[todo] = texts[todo].astype(str).map(guess)

    target = columns.get("strat_name", "strat_name")
    if target in df:
        df[target] = df[target].mask(_blank(df[target]), guessed)
    else:
        df[target] = guessed
    return df


def strip_z(g: BaseGeometry | None):
    """Return a 2-D copy of *g* (or None)."""
    if g is None or g.is_empty or not g.has_z:
        return g  # already 2D / empty / null
    return wkt.loads(wkt.dumps(g, output_dimension=2))


_PACKAGES = "Map packages"


def ingest_map(
    slug: Annotated[
        str,
        Argument(
            help="Slug for the map, or a Macrostrat map package (.gpkg) to import"
        ),
    ],
    files: Annotated[
        Optional[List[Path]],
        Argument(help="GIS files to ingest, or map packages to import `slug` from"),
    ] = None,
    embed: bool = False,
    crs: str = None,
    pipeline: Annotated[
        str,
        Option(
            help="Metadata pipeline, required with --meta-path: " + ", ".join(PIPELINES)
        ),
    ] = "",
    if_exists: str = "replace",
    meta_path: str = None,
    # TODO add default key column to the first column in the file
    merge_key: str = None,
    meta_table: str = "polygons",
    chunksize: int = 100,
    feature_types: List[str] = None,
    on_conflict: Annotated[
        ConflictAction,
        Option(
            help="For a slug that already exists: ask, overwrite, skip or stop",
            rich_help_panel=_PACKAGES,
        ),
    ] = ConflictAction.ask,
    sources_schema: Annotated[
        bool,
        Option(
            help="Load the package's `sources.*` staging tables",
            rich_help_panel=_PACKAGES,
        ),
    ] = True,
    yes: Annotated[
        bool,
        Option(
            "--yes",
            "-y",
            help="Skip the confirmation prompt where one is allowed",
            rich_help_panel=_PACKAGES,
        ),
    ] = False,
) -> Tuple[str, str, str]:
    """Ingest general GIS data files into the database.

    This is similar to the macrostrat maps pipeline ingest-map command,
    but it doesn't upload files to S3 or check their existence.

    A Macrostrat map package (from `macrostrat maps export`) is imported
    instead: `ingest maps.gpkg` loads every map in it, and
    `ingest 'ngs-*' maps.gpkg` only the slugs matching the pattern.
    """
    files = list(files or [])
    packages, only = _map_packages(slug, files)
    if packages:
        from ..package.cli import ingest_packages

        return ingest_packages(
            packages,
            only=only,
            on_conflict=on_conflict,
            staging=sources_schema,
            yes=yes,
        )
    if not files:
        raise IngestError("No files to ingest")
    # The pipeline is the one asked for, never inferred from meta_path's extension.
    if meta_path and pipeline not in PIPELINES:
        raise IngestError(
            f"With a metadata path, --pipeline must be one of {', '.join(PIPELINES)}"
            f" (got {pipeline!r})"
        )

    db = get_database()

    console.print("[bold]Ingesting map data for source [bold blue]" + slug)
    # Read file with GeoPandas and dump to PostGIS

    # We need to put multigeometries first
    frames = defaultdict(list)

    # Add to map-sources table
    db.run_sql(
        "INSERT INTO maps.sources (primary_table, slug) VALUES (:table, :slug) ON CONFLICT DO NOTHING",
        dict(table=staging_table(check_slug(slug), "polygons"), slug=slug),
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
        # feature_types restricts which sources.<slug>_<suffix> tables get written,
        # so a single layer can be re-ingested without replacing the others.
        if feature_types is not None and feature_type not in feature_types:
            console.print(f"[dim]Skipping {feature_type}s (not requested)[/dim]")
            continue
        # Concatenate the layers that have features of this type. An empty slice
        # still carries its layer's columns: GeMS's empty GeochronPoints put an
        # `age` on every polygon frame, which sent the legend's age to `age_meta`.
        # With no features at all, one empty frame keeps the flow below as it was.
        df_list = [d for d in df_list if len(d)] or df_list[:1]
        df = G.GeoDataFrame(P.concat(df_list, ignore_index=True))
        df = df.loc[:, ~df.columns.duplicated()]
        feature_suffix = feature_type.lower() + "s"
        if feature_suffix == "linestrings":
            feature_suffix = "lines"
        # preprocess dataframe will take the concatenated polygons, lines, or points df and see if there are any metadata
        # formatted_filenames to append and map based on the pipeline the user chose
        if meta_path:
            df.columns = df.columns.str.lower()
            df, ingest_pipeline, comments, state = preprocess_dataframe(
                db,
                df,
                meta_path=meta_path,
                join_col=join_col.lower(),
                feature_suffix=feature_suffix,
                pipeline=pipeline,
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
        if feature_suffix == "polygons":
            df = map_strat_name_ingest(db, df)
            if "strat_name" not in df or _blank(df["strat_name"]).all():
                ingest_results["comments"] = "; ".join(
                    filter(None, [ingest_results["comments"], "No strat_names found."])
                )
        console.print(f"[bold]{feature_type}s[/bold] [dim]- {len(df)} features[/dim]")
        console.print("Columns:")
        for col in df.columns:
            console.print(f"- {col}")

        table = f"{table_prefix(slug)}_{feature_suffix}"
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

            if len(df) == 0:
                console.print(f"[yellow]Skipping {feature_suffix}: 0 features[/yellow]")
                continue
            df["geometry"] = df["geometry"].apply(strip_z)
            df = df.dropna(axis=1, how="all")

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


def _map_packages(slug: str, files: List[Path]):
    """The map packages named on the command line, and the slugs to take.

    Returns `(None, None)` for an ordinary ingest.
    """
    from ..package.format import is_map_package

    slug_is_package = is_map_package(slug)
    candidates = [Path(slug), *files] if slug_is_package else files
    packages = [Path(f) for f in candidates if is_map_package(f)]
    if not packages:
        return None, None
    if len(packages) != len(candidates):
        raise IngestError("Map packages can't be ingested alongside other files")
    return packages, None if slug_is_package else [slug]


def create_dataframe_for_layer(file: Path, layer: str) -> G.GeoDataFrame:
    return G.read_file(file, layer=layer)


def get_dataframes(files) -> Iterable[Tuple[str, G.GeoDataFrame]]:
    single_file = len(files) == 1
    # Every spatial layer is read. A dataset's own exclusions (cross sections,
    # topology errors, annotation) belong to its pipeline, which can narrow the
    # list `get_layer_names` returns; see `Maps/Arizona/ingest.py` in
    # data-integration.
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
            df.columns = df.columns.str.replace(r"\s+", " ", regex=True).str.strip()

            info = get_layer_info(file, layer)
            # Apply domains for Geodatabase linked information

            df = apply_domains_to_fields(df, info)

            # TODO: find and follow foreign key relationships

            # Non-spatial tables (e.g. DescriptionOfMapUnits) come back as plain
            # DataFrames with no .crs, and can't contribute to the polygon/line/point
            # frames. They are read separately via extract_gdb_layer when needed.
            if "geometry" not in df.columns:
                console.print(
                    f"[yellow dim]Skipping {layer}: no geometry column[/yellow dim]"
                )
                continue

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
