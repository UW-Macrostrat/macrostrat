import re
from typing import Optional

import fiona
import geopandas as G
import pandas as pd
import pyogrio

from ..database import get_database


def extract_gdb_layer(legend_path, layer_name, read_geometry):
    """Return a GeoDataFrame containing the requested non‑spatial or spatial layer.
    Parameters:
    legend_path: Pathlike or str. Path to the .gdb directory.
    layer_name: str. Case‑insensitive substring to identify the target layer (for example "DescriptionOfMapUnits").
        Can be spatial or nonspatial.
    read_geometry: bool. Passed through to gpd.read_file to control whether geometry columns are read.

    Returns
    GeoDataFrame or None: The requested layer, or None when no matching layer is found or an error occurs.
    """

    dmu_layer = None

    try:
        # we are trying to read all of the non-spatial layers in the .gdb
        # ingest any non-spatial metadata from .gdb just specify the file name in the re.search function
        # ex. GeoMaterialDict or DescriptionOfMapUnits
        # then we merge legend_df into the polygons df on a join_col
        for name in fiona.listlayers(legend_path):
            if re.search(rf"{layer_name}", name, re.IGNORECASE):
                dmu_layer = name
        if dmu_layer is None:
            print(
                f"[yellow]No {layer_name} table found in "
                f"{legend_path.name}.  Layers: "
                f"{', '.join(fiona.listlayers(legend_path))}[/yellow]"
            )
            return None
        legend_df = G.read_file(
            legend_path,
            layer=dmu_layer,
            engine="pyogrio",
            read_geometry=read_geometry,
        )
        return legend_df
    except ValueError as e:
        print(f"[red]Error {e}[/red]\n")
        return None


def transform_gdb_layer(legend_df: G.GeoDataFrame) -> G.GeoDataFrame:
    """Map column names to Macrostrat standard and concatenate lithology‑related fields.
    Parameters:
    legend_df: G.GeoDataFrame. Raw DMU layer as extracted from extract_gdb_layer().

    Returns:
    G.GeoDataFrame. A normalized GeoDataFrame with lower cased column names,canonical field names
        (``descrip``, ``strat_name`` …), a single lith column that concatenates lithology descriptors, and
        empty columns removed.
    """
    rename_map = {
        "description": "descrip",
        "name": "name",
        "fullname": "strat_name",
        "age": "age",
        "descriptionofmapunits_id": "orig_id",
        "notes": "comments",
        "areafillrgb": "color",
        "label": "strat_symbol",
    }
    legend_df.columns = legend_df.columns.str.lower()

    legend_df = legend_df.rename(
        columns={c: rename_map[c] for c in rename_map if c in legend_df}
    )

    lith_cols = [c for c in ("generallithology", "geomaterial") if c in legend_df]
    if lith_cols:
        legend_df["lith"] = (
            legend_df[lith_cols]
            .fillna("")
            .agg("; ".join, axis=1)
            .str.strip("; ")
            .replace("", pd.NA)
        )
        legend_df = legend_df.drop(columns=lith_cols)
    legend_df = legend_df.dropna(axis=1, how="all")
    return legend_df


# determine if name AND description field is proper or not to insert into the strat_name (group, member, formation, null otherwise)
# comma separated list of strat_names. similar to lith field.
# geolex...
def infer_strat_names():
    pass


def get_age_interval_df() -> pd.DataFrame:
    """Query and store interval names from the database into a DataFrame for lookups.
    Returns:
    pd.DataFrame. A pandas series with interval_name strings.
    """
    db = get_database()
    query = "SELECT interval_name FROM macrostrat.intervals"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


QUALIFIERS = {"early", "middle", "late", "lower", "upper"}


def lookup_and_validate_age(
    name: str | float, interval_set: set[str]
) -> tuple[Optional[str], Optional[str]]:
    """
    Return (b_interval, t_interval) for the first interval(s) found.
    If only one valid interval is found, duplicate it into both slots.
    """
    # findall() takes the legend_df["name"] and splits each word into an array of strings.

    tokens = re.findall(r"\b\w+\b", str(name).lower())

    for i, word in enumerate(tokens):
        qual = "early" if word == "lower" else "late" if word == "upper" else word

        if word in QUALIFIERS and i + 3 < len(tokens) and tokens[i + 2] in QUALIFIERS:
            next_qual = (
                "early"
                if tokens[i + 2] == "lower"
                else "late" if tokens[i + 2] == "upper" else tokens[i + 2]
            )
            phrase_one = f"{qual} {tokens[i + 3]}"
            phrase_two = f"{next_qual} {tokens[i + 3]}"
            if phrase_one in interval_set and phrase_two in interval_set:
                # this is true if word is early or middle
                return (
                    (phrase_one, phrase_two)
                    if qual == "early" and next_qual in {"middle", "late"}
                    else (phrase_two, phrase_one)
                )
            elif phrase_one in interval_set:
                return phrase_one, phrase_one
            elif phrase_two in interval_set:
                return phrase_two, phrase_two
            elif tokens[i + 3] in interval_set:
                return tokens[i + 3], tokens[i + 3]

        if word in QUALIFIERS and i + 1 < len(tokens):
            phrase = f"{qual} {tokens[i + 1]}"
            if phrase in interval_set:
                return phrase, phrase
        if word in interval_set:
            return word, word
    return pd.NA, pd.NA


# need to modify this logic and maybe need to reference another table besides intervals.
# look in the name and age column to infer the age
def map_t_b_intervals(legend_df: G.GeoDataFrame) -> G.GeoDataFrame:
    """Populate the b_interval field using age and name information.
    The function first tries a direct match between legend_df.age and the
    canonical interval list. For formations whose age is not explicit, it scans
    the formation name for any word that appears in the interval list.
    Parameters:
    legend_df : G.GeoDataFrame. Legend table with at least age and name columns.

    Returns:
    G.GeoDataFrame: The input frame with a newly filled/created b_interval column.
    """
    interval_df = get_age_interval_df().reset_index(drop=True)
    interval_df["interval_name"] = interval_df["interval_name"].str.lower()
    legend_df["age"] = legend_df["age"].str.lower()
    legend_df["name"] = legend_df["name"].str.lower()
    interval_set = set(interval_df["interval_name"].dropna().str.lower().unique())
    # map age fields to b/t intervals
    # must have a match in the macrotrat.intervals dictionary in order to return a valid interval
    legend_df[["b_interval", "t_interval"]] = (
        legend_df["age"]
        .str.lower()
        .apply(
            lambda n: pd.Series(
                lookup_and_validate_age(n, interval_set),
                index=["b_interval", "t_interval"],
            )
        )
    )
    # for the rest of NA's we will map the name field to b/t intervals
    needs_fill = legend_df["b_interval"].isna()
    legend_df.loc[needs_fill, ["b_interval", "t_interval"]] = (
        legend_df.loc[needs_fill, "name"]
        .str.lower()
        .apply(
            lambda n: pd.Series(
                lookup_and_validate_age(n, interval_set),
                index=["b_interval", "t_interval"],
            )
        )
    )
    return legend_df
