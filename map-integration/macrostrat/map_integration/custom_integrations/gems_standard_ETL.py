import fiona
import pyogrio
import geopandas as G
import pandas as pd
import re
from ..database import get_database

def extract_gdb_layer(legend_path, layer_name, read_geometry):
    dmu_layer = None
    gdb_layer_names = fiona.listlayers(legend_path)
    try:
        # we are trying to read all of the non-spatial layers in the .gdb
        # ingest any non-spatial metadata from .gdb just specify the file name in the re.search function
        # ex. GeoMaterialDict or DescriptionOfMapUnits
        # then we merge legend_df into the polygons df on a join_col
        for name in fiona.listlayers(legend_path):
            print(name)
            if re.search(rf"{layer_name}", name, re.I):
                dmu_layer = name
        if dmu_layer is None:
            print(f"[yellow]No {layer_name} table found in "
                          f"{legend_path.name}.  Layers: "
                          f"{', '.join(fiona.listlayers(legend_path))}[/yellow]")
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


def transform_gdb_layer(legend_df: G.DataFrame) -> G.DataFrame:
    rename_map = {
        "description": "descrip",
        "name": "name",
        "fullname": "strat_name",
        "age": "age",
        "descriptionofmapunits_id": "orig_id",
        "notes": "comments",
        "areafillrgb": "color",
        "label": "strat_symbol"
    }
    legend_df.columns = legend_df.columns.str.lower()

    legend_df = legend_df.rename(columns={c: rename_map[c] for c in rename_map if c in legend_df})

    lith_cols = [c for c in ("generallithology", "geomaterial") if c in legend_df]
    if lith_cols:
        legend_df["lith"] = (
            legend_df[lith_cols].fillna("").agg("; ".join, axis=1)
            .str.strip("; ").replace("", pd.NA)
        )
        legend_df = legend_df.drop(columns=lith_cols)
    legend_df = legend_df.dropna(axis=1, how="all")
    return legend_df

#determine if name AND description field is proper or not to insert into the strat_name (group, member, formation, null otherwise)
#comma separated list of strat_names. similar to lith field.
#geolex...
def infer_strat_names():
    pass


def get_age_interval_df() -> pd.DataFrame:
    db = get_database()
    query = "SELECT interval_name FROM macrostrat.intervals"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df
def first_interval_word_from_name(name: str | float) -> str | pd.NA:
    """
    For a given unit name (may be NaN), return the *original‑casing* word
    that matches any interval name. If none match, return pd.NA.
    """
    interval_set = set(
        interval_df["interval_name"]
        .dropna()
        .str.lower()
        .unique()
    )

    # break the name into individual words; \w+ = letters, digits, underscore
    for word in re.findall(r"\b\w+\b", str(name)):
        if word.lower() in interval_set:
            return word  # return the word exactly as it appears in 'name'
    return pd.NA


#need to modify this logic and maybe need to reference another table besides intervals.
#look in the name and age column to infer the age
def map_t_b_intervals(legend_df: G.DataFrame) -> G.DataFrame:
    interval_df = get_age_interval_df().reset_index(drop=True)
    interval_df["interval_name"] = interval_df["interval_name"].str.lower()
    legend_df["age"] = legend_df["age"].str.lower()
    legend_df["name"] = legend_df["name"].str.lower()
    interval_set = set(
        interval_df["interval_name"]
        .dropna()
        .str.lower()
        .unique()
    )

    mask = legend_df["age"].isin(interval_df["interval_name"])
    legend_df["b_interval"] = legend_df["age"].where(mask)

    # ── 3.  fill the remaining NaNs row‑by‑row by scanning 'name' ───────────────
    needs_fill = legend_df["b_interval"].isna()

    legend_df.loc[needs_fill, "b_interval"] = (
        legend_df.loc[needs_fill, "name"].apply(first_interval_word_from_name)
    )

    # optional: inspect
    display(legend_df.head(50))

    return df