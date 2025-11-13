import re
from typing import Optional, Tuple

import fiona
import geopandas as G
import pandas as pd
import pyogrio

from ..database import get_database


def extract_gdb_layer(
    meta_path, layer_name, read_geometry
) -> Tuple[G.GeoDataFrame, str, str]:
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
    ingest_pipeline = ""
    comments = ""
    # we are trying to read all of the non-spatial layers in the .gdb
    # ingest any non-spatial metadata from .gdb just specify the file name in the re.search function
    # ex. GeoMaterialDict or DescriptionOfMapUnits
    # then we merge meta_df into the polygons df on a join_col
    for name in fiona.listlayers(meta_path):
        if name in (
            "DescriptionOfMapUnits",
            "GeoMaterialDict",
            "DataSources",
            "Glossary",
        ):
            ingest_pipeline = "Gems pipeline"
        if re.search(rf"{layer_name}", name, re.IGNORECASE):
            dmu_layer = name
    if dmu_layer is None and ingest_pipeline == "Gems pipeline":
        comments = f"[yellow]No {layer_name} table found in {meta_path.name}.  Layers:{', '.join(fiona.listlayers(meta_path))}[/yellow]"
        return None, ingest_pipeline, comments
    elif dmu_layer is None and ingest_pipeline == "":
        ingest_pipeline = ".gdb pipeline"
        comments = "Basic .gdb ingestion. No gems layers found."
        return None, ingest_pipeline, comments
    meta_df = G.read_file(
        meta_path,
        layer=dmu_layer,
        engine="pyogrio",
        read_geometry=read_geometry,
    )
    return meta_df, ingest_pipeline, comments


def transform_gdb_layer(meta_df: G.GeoDataFrame) -> Tuple[G.GeoDataFrame, str]:
    """Map column names to Macrostrat standard and concatenate lithology‑related fields.
    Parameters:
    legend_df: G.GeoDataFrame. Raw DMU layer as extracted from extract_gdb_layer().

    Returns:
    G.GeoDataFrame. A normalized GeoDataFrame with lower cased column names,canonical field names
        (``descrip``, ``strat_name`` …), a single lith column that concatenates lithology descriptors, and
        empty columns removed.
    """
    comments = ""
    required_canonical = {
        "name",
        "strat_name",
        "age",
        "descrip",
        "color",
        "strat_symbol",
    }
    rename_map = {
        "name": "name",
        "fullname": "strat_name",
        "age": "age",
        "age_meta": "age",
        "hierarchykey": "orig_id",
        "notes": "comments",
        "label": "strat_symbol",
        "description": "descrip",
        "descr": "descrip",
        "areafillrgb": "color",
        "rgb": "color",
    }
    meta_df.columns = meta_df.columns.str.lower()
    meta_df = meta_df.rename(
        columns={src: dst for src, dst in rename_map.items() if src in meta_df.columns}
    )
    missing_canonical = required_canonical - set(meta_df.columns)
    if missing_canonical:
        # which dmu keys would have supplied those canonical fields?
        missing_sources = {
            src for src, dst in rename_map.items() if dst in missing_canonical
        }
        comments = f"Gems DMU columns not found: {sorted(missing_sources)}."

    lithology_candidates = ("generallithology", "geomaterial")
    lith_cols = [c for c in lithology_candidates if c in meta_df]
    if lith_cols:
        meta_df["lith"] = (
            meta_df[lith_cols]
            .fillna("")
            .agg("; ".join, axis=1)
            .str.strip("; ")
            .replace("", pd.NA)
        )
        meta_df = meta_df.drop(columns=lith_cols)
    else:
        comments += f"Missing lithology columns: {lithology_candidates}."
    meta_df = meta_df.dropna(axis=1, how="all")
    return meta_df, comments


def get_strat_names_df() -> pd.DataFrame:
    """Query and store interval names from the database into a DataFrame for lookups.
    Returns:
    pd.DataFrame. A pandas series with interval_name strings.
    """
    db = get_database()
    query = "select rank_name from macrostrat.lookup_strat_names"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


STRAT_NAME_LOOKUP = {"formation", "fm", "bed", "member", "mbr", "group"}
IRRELEVANT_WORDS = {
    "active",
    "percent",
    "relief",
    "part",
    "area",
    "m",
    "above",
    "cm",
    "fine",
    "in",
    "dacite",
    "conglomerate",
    "top",
    "an",
    "map",
    "tcg",
    "quadrangle",
    "to",
    "part",
    "late",
    "middle",
    "lack",
    "any",
    "evidence",
    "sand",
    "gravel",
    "silt",
    "composed",
    "well",
    "sorted",
    "and",
    "a",
    "is",
    "or",
    "for",
    "trachyte",
    "unit",
    "of",
    "the",
}
VALID_WORDS = {"plomosa", "suizo", "coronado", "complex", "units", "sasco"}


def lookup_and_validate_strat_name(
    name_descrip: str | float, rank_name_set: set[str]
) -> Optional[str]:
    """
    Return the full stratigraphic name found in the tokenized input string.
    Looks for STRAT_NAME_LOOKUP terms and matches the preceding token + current token against known strat names.
    """
    tokens = re.findall(r"\b\w+\b", str(name_descrip).lower())
    for i, qualifier in enumerate(tokens):
        candidate_indices = [i - 3, i - 2, i - 1, i]
        phrase_array = []
        phrase_array_dropped = []
        of_indices = [i - 1, i, i + 1, i + 2, i + 3]
        if qualifier in STRAT_NAME_LOOKUP:
            for j in candidate_indices:
                if 0 <= j < len(tokens):
                    phrase_array.append(tokens[j])
            phrase_array_dropped = [
                word for word in phrase_array if word not in IRRELEVANT_WORDS
            ]
        elif qualifier == "of" and i + 1 < len(tokens) and tokens[i + 1] != "the":
            for j in of_indices:
                if 0 <= j < len(tokens):
                    phrase_array.append(tokens[j])
            phrase_array_dropped = [
                word for word in phrase_array if word not in IRRELEVANT_WORDS
            ]
        if len(phrase_array_dropped) > 0:
            strat_name = " ".join(phrase_array).title()
            for word in phrase_array_dropped:
                if word in VALID_WORDS:
                    return strat_name
            for rank_name in rank_name_set:
                rank_name = rank_name.lower()
                match_count = sum(
                    1 for word in phrase_array_dropped if word in rank_name
                )
                match_ratio = match_count / len(phrase_array_dropped)
                # if match_ratio == 1:
                # return rank_name
                if match_ratio >= 0.6:
                    return strat_name
    return pd.NA


def map_strat_name(meta_df: G.GeoDataFrame) -> G.GeoDataFrame:
    """
    Update legend_df with a new column 'ranked_strat_name' based on matched strat names.
    Looks for rank words and matches against known stratigraphic names.

    Parameters:
    - legend_df: GeoDataFrame containing a column of unit names.
    - name_col: The name of the column in legend_df to search.

    Returns:
    - GeoDataFrame with an additional 'ranked_strat_name' column.
    """
    rank_name_df = get_strat_names_df()
    rank_name_set = set(rank_name_df["rank_name"].dropna().unique())
    # check name for matched strat_name
    meta_df["strat_name"] = (
        meta_df["name"]
        .str.lower()
        .apply(lambda n: lookup_and_validate_strat_name(n, rank_name_set))
    )

    # fallback to 'descrip' for missing values
    needs_fill = meta_df["strat_name"].isna()
    meta_df.loc[needs_fill, "strat_name"] = (
        meta_df.loc[needs_fill, "descrip"]
        .str.lower()
        .apply(lambda d: lookup_and_validate_strat_name(d, rank_name_set))
    )

    return meta_df


def get_age_interval_df() -> pd.DataFrame:
    """Query and store interval names from the database into a DataFrame for lookups.
    Returns:
    pd.DataFrame. A pandas series with interval_name strings.
    """
    db = get_database()
    query = "SELECT id, interval_name FROM macrostrat.intervals"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


QUALIFIERS = {"early", "middle", "late", "lower", "upper"}
QUALIFIER_ORDER = {"early": 0, "middle": 1, "late": 2}


def lookup_and_validate_age(
    name: str, interval_lookup: dict[str, int]
) -> tuple[Optional[int], Optional[int]]:
    """
    Return (b_interval, t_interval) for the first interval(s) found.
    If only one valid interval is found, duplicate it into both slots.
    """
    s = str(name).lower().replace("–", "-").strip()
    if "-" in s:
        left, right = [p.strip() for p in s.split("-", 1)]
        if left in interval_lookup and right in interval_lookup:
            return interval_lookup[left], interval_lookup[right]
        elif left in interval_lookup and right not in interval_lookup:
            return interval_lookup[left], interval_lookup[left]
        elif left not in interval_lookup and right in interval_lookup:
            return interval_lookup[right], interval_lookup[right]

    tokens = re.findall(r"\b\w+\b", s)

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
            if phrase_one in interval_lookup and phrase_two in interval_lookup:
                # this is true if word is early or middle
                return (
                    (interval_lookup[phrase_one], interval_lookup[phrase_two])
                    if QUALIFIER_ORDER.get(qual, -1)
                    < QUALIFIER_ORDER.get(next_qual, -1)
                    else (interval_lookup[phrase_two], interval_lookup[phrase_one])
                )
            elif phrase_one in interval_lookup:
                return interval_lookup[phrase_one], interval_lookup[phrase_one]
            elif phrase_two in interval_lookup:
                return interval_lookup[phrase_two], interval_lookup[phrase_two]
            elif tokens[i + 3] in interval_lookup:
                return interval_lookup[tokens[i + 3]], interval_lookup[tokens[i + 3]]

        if word in QUALIFIERS and i + 1 < len(tokens):
            phrase = f"{qual} {tokens[i + 1]}"
            if phrase in interval_lookup:
                return interval_lookup[phrase], interval_lookup[phrase]
        if word in interval_lookup:
            return interval_lookup[word], interval_lookup[word]
    return pd.NA, pd.NA


# need to modify this logic and maybe need to reference another table besides intervals.
# look in the name and age column to infer the age
def map_t_b_intervals(meta_df: G.GeoDataFrame) -> G.GeoDataFrame:
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
    interval_lookup = {
        row["interval_name"].lower(): row["id"] for _, row in interval_df.iterrows()
    }

    # map age fields to b/t intervals
    # must have a match in the macrotrat.intervals dictionary in order to return a valid interval
    meta_df[["b_interval", "t_interval"]] = (
        meta_df["age"]
        .str.lower()
        .apply(
            lambda n: pd.Series(
                lookup_and_validate_age(n, interval_lookup),
                index=["b_interval", "t_interval"],
            )
        )
    )
    # for the rest of NA's we will map the name field to b/t intervals
    needs_fill = meta_df["b_interval"].isna()

    if needs_fill.any():
        meta_df.loc[needs_fill, ["b_interval", "t_interval"]] = (
            meta_df.loc[needs_fill, "name"]
            .str.lower()
            .apply(
                lambda n: pd.Series(
                    lookup_and_validate_age(n, interval_lookup),
                    index=["b_interval", "t_interval"],
                )
            )
        )
    return meta_df

def map_points_to_preferred_fields(meta_df: G.GeoDataFrame) -> G.GeoDataFrame:
    rename_map = {
        "Symbol": "orig_id",
        "Label": "descrip",
        "Notes": "comments",
        "Azimuth": "strike",
        "Inclination": "dip",
        "SymbolRotation": "dip_dir",
        "Type": "point_type",
        "IdentityConfidence": "certainty"

    }
    col_lower_to_actual = {col.lower(): col for col in meta_df.columns}
    actual_rename = {}
    for src, dst in rename_map.items():
        src_lower = src.lower()
        if src_lower in col_lower_to_actual:
            actual_rename[col_lower_to_actual[src_lower]] = dst

    meta_df = meta_df.rename(columns=actual_rename)
    return meta_df

def map_lines_to_preferred_fields(meta_df: G.GeoDataFrame) -> G.GeoDataFrame:
    rename_map = {
        "Symbol": "orig_id",
        "Notes": "descrip",
        "Label": "name",
        "Type": "type",
        "Azimuth": "direction"
    }

    col_lower_to_actual = {col.lower(): col for col in meta_df.columns}
    actual_rename = {}
    for src, dst in rename_map.items():
        src_lower = src.lower()
        if src_lower in col_lower_to_actual:
            actual_rename[col_lower_to_actual[src_lower]] = dst

    meta_df = meta_df.rename(columns=actual_rename)
    return meta_df


