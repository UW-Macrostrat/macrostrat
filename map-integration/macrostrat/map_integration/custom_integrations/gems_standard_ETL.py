import fiona
import pyogrio
import geopandas as G
import pandas as pd
import re
from ..database import get_database

def extract_gdb_layer(legend_path, layer_name, polygon_df, read_geometry):
    dmu_layer = None
    gdb_layer_names = fiona.listlayers(legend_path)
    print("HERE ARE THE GDB LAYER NAMES FOR metadata merge", gdb_layer_names)
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
        legend_df.columns = legend_df.columns.str.lower()
        return legend_df
    except ValueError as e:
        print(f"[red]Error {e}[/red]\n")
        return None


def transform_gdb_layer(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "orig_id": "hierarchykey",
        "description": "descrip",
        "name": "name",
        "fullname": "strat_name",
        "age": "age",
        "mapunitpolys_id": "orig_id",
        "notes": "comments",
    }
    df = df.rename(columns={c: rename_map[c] for c in rename_map if c in df})
    lith_cols = [c for c in ("generallithology", "geomaterial") if c in df]
    if lith_cols:
        df["lith"] = (
            df[lith_cols].fillna("").agg("; ".join, axis=1)
            .str.strip("; ").replace("", pd.NA)
        )
        df = df.drop(columns=lith_cols)
    print('\n', df.columns.tolist())
    print("TRANSFORM dataframe!!!!", df.head(5))
    return df


def get_age_interval_df() -> pd.DataFrame:
    db = get_database()
    query = "SELECT * FROM macrostrat.intervals ORDER BY id"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


#need to modify this logic and maybe need to reference another table besides intervals.
def map_t_b_intervals(df: pd.DataFrame) -> pd.DataFrame:
    intervals = get_age_interval_df().reset_index(drop=True)
    intervals["t_interval"] = intervals["interval_name"].shift(-1)  # row before
    intervals["b_interval"] = intervals["interval_name"].shift(1)   # row after
    t_map = intervals.set_index("interval_name")["t_interval"].to_dict()
    b_map = intervals.set_index("interval_name")["b_interval"].to_dict()
    df["t_interval"] = df["age"].map(t_map)
    df["b_interval"] = df["age"].map(b_map)
    return df