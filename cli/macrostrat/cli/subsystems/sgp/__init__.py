"""
Subsystem for SGP matching
"""

from unittest.mock import inplace

from dynaconf.utils import deduplicate
from numpy.f2py.crackfortran import verbose
from rich.progress import Progress
from typer import Typer

from .clean_strat_name import (
    clean_strat_name,
    format_name,
    StratNameTextMatch,
    StratRank,
    clean_strat_name_text,
)
from ...database import get_db
from macrostrat.core import app
from macrostrat.database import Database
from pathlib import Path
from rich import print
from geopandas import GeoDataFrame, sjoin
from shapely.geometry import Point
from sqlalchemy.sql import text
from pandas import read_sql, Series

sgp = Typer(name="sgp", no_args_is_help=True)

here = Path(__file__).parent


def get_columns_data_frame():
    """Get all Macrostrat columns as a GeoDataFrame"""
    M = get_db()
    sql = """
        SELECT col_id, ST_SetSRID(ca.col_area, 4326) as col_area
        FROM macrostrat.col_areas ca
        JOIN macrostrat.cols c
          ON c.id = ca.col_id
        WHERE c.status_code = 'active'
    """
    gdf = GeoDataFrame.from_postgis(
        text(sql), M.engine.connect(), geom_col="col_area", index_col="col_id"
    )
    return gdf


@sgp.command(
    name="match-units",
)
def import_sgp_data(verbose: bool = False):
    M = get_db()

    # TODO: simplify this
    uri = M.engine.url.set(database="sgp")
    uri_ = str(uri).replace("***", uri.password)
    sgp_db = Database(uri_)

    sql = here / "measurements-to-match.sql"

    columns = get_columns_data_frame()

    samples = GeoDataFrame.from_postgis(
        text(sql.read_text()),
        sgp_db.engine.connect(),
        geom_col="geom",
        index_col="sample_id",
    )

    # Join samples to columns

    sample_locs = samples.drop(columns=[i for i in samples.columns if i != "geom"])

    join = sjoin(sample_locs, columns, how="left", op="intersects")
    grouped = join.groupby("sample_id")
    counts = grouped.size().value_counts()
    res = grouped.aggregate("first")
    res.rename(columns={"index_right": "col_id"}, inplace=True)
    res.drop(columns=["geom"], inplace=True)

    n_total = len(res)
    n_too_many = counts[counts.index > 1].sum()
    n_matched = counts[1]
    n_not_matched = counts.get(0, 0)

    app.console.print(
        f"Matched {n_matched} of {n_total} measurements to a Macrostrat column.",
        style="green",
    )

    if n_too_many > 0:
        app.console.print(
            f"{n_too_many} measurements have multiple matched columns.", style="yellow"
        )
    if n_not_matched > 0:
        app.console.print(
            f"{n_not_matched} measurements have no matched columns.", style="yellow"
        )
    if n_too_many + n_not_matched == 0:
        app.console.print("All measurements matched to a single column.", style="green")

    # Augment the samples with the matched column
    samples = samples.join(res, on="sample_id")

    samples["source_text"] = samples.apply(merge_text, axis=1)

    # Delete now-extraneous columns
    for original_column in ["member", "formation", "group", "verbatim_strat"]:
        samples.drop(columns=[original_column], inplace=True)

    # Group by column and strat names; these will be our matching groups
    counts = samples.groupby(["col_id", "source_text"]).size().reset_index(name="count")

    # Make sure that we can group by strat names
    counts["strat_names"] = (
        counts["source_text"]
        .apply(standardize_names)
        .apply(deduplicate_strat_names)
        .apply(lambda x: tuple(sorted(x)))
    )

    app.console.print(f"Grouped {len(counts)} unique stratigraphic name groups.")

    if verbose:
        for ix, row in counts.iterrows():
            print(f"{row['count']} samples in column {row['col_id']}")
            print("  " + format_names(row["strat_names"]))
        print()

    # Summarize the counts
    match = counts["strat_names"].apply(lambda x: len(x) > 0)
    print_counts("candidate stratigraphic name", counts[match], n_total)

    # Create an empty column for matched units
    counts["match"] = None

    success = 0
    total = 0
    with M.engine.connect() as conn:
        for ix, row in counts.iterrows():
            match = get_matched_unit(conn, row["col_id"], row["strat_names"])
            message = ": [red bold]no match[/]"
            if match is not None:
                success += 1
                counts[ix, "match"] = match
                message = f" → {match.strat_name_clean}"
            total += 1
            print(
                f"{success}/{total}: [dim italic]{row.source_text}[/] → {format_names(row.strat_names)} {message}"
            )

    match = counts["match"].notnull()
    print_counts("matched unit", counts[match], n_total)


def print_counts(category, subset, target):
    match_count = subset["count"].sum()
    app.console.print(
        f"{match_count} samples have at least one {category}.",
        style="green bold" if match_count == target else None,
    )
    if match_count < target:
        app.console.print(
            f"{target - match_count} samples have no {category}.",
            style="yellow",
        )


def format_names(strat_names):
    return ", ".join([format_name(i) for i in strat_names])


_column_unit_index = {}


def get_column_units(conn, col_id):
    """
    Get a unit that matches a given stratigraphic name
    """
    global _column_unit_index

    M = get_db()

    sql = Path(__file__).parent / "column-strat-names.sql"

    if col_id in _column_unit_index:
        return _column_unit_index[col_id]

    units_df = read_sql(
        text(sql.read_text()),
        conn,
        params=dict(col_id=col_id, use_concepts=True, use_adjacent_cols=True),
        coerce_float=False,
    )

    units_df["strat_name_clean"] = units_df["strat_name"].apply(clean_strat_name_text)

    _column_unit_index[col_id] = units_df
    return units_df


def get_matched_unit(conn, col_id, strat_names):
    """
    Get a unit that matches a given stratigraphic name
    """

    units = get_column_units(conn, col_id)
    u1 = units[units.strat_name_clean != None]

    u1.sort_values(by="strat_name_clean", inplace=True)

    for strat_name in strat_names:
        # Try for an exact match with all strat names
        for ix, row in u1.iterrows():
            name = row["strat_name_clean"]
            if strat_name.name == name:
                return row

    return None


def standardize_names(source_text):
    res = []
    names = source_text.split(";")
    for name in names:
        out_name = clean_strat_name(name)
        for n1 in out_name:
            res.append(n1)
    return res


def merge_text(row):
    names = []
    for level in ["member", "formation", "group"]:
        lvl = row.get(level, None)
        if lvl is not None:
            names.append(lvl + " " + level.capitalize())
    lvl = row.get("verbatim_text", None)
    if lvl is not None:
        names.append(lvl)
    return "; ".join(names)


def match_samples_to_column_units(df):
    # Get the column units
    M = get_db()
    sql = """
        SELECT * FROM macrostrat.units u
        WHERE u.col_id = :col_id
    """
    units = read_sql(
        text(sql), M.engine.connect(), params={"col_id": int(df["col_id"].iloc[0])}
    )
    import IPython

    IPython.embed()
    raise


def deduplicate_strat_names(samples):
    return list(set(samples))
