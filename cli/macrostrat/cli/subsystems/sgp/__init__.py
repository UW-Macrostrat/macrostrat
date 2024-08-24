"""
Subsystem for SGP matching
"""

from unittest.mock import inplace

from dynaconf.utils import deduplicate
from numpy.f2py.crackfortran import verbose
from typer import Typer

from .clean_strat_name import (
    clean_strat_name,
    format_name,
    StratNameTextMatch,
    StratRank,
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

    # Sample first 1000 rows
    samples = samples.head(1000)

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

    for level in ["member", "formation", "group"]:
        standardize_strat_column(samples, level, add_suffix=" " + level.capitalize())
    # Standardize the strat names
    standardize_strat_column(samples, "verbatim_strat")

    samples["strat_names"] = samples["strat_names"].apply(deduplicate_strat_names)

    # Make sure that we can group by strat names
    samples["strat_names"] = samples["strat_names"].apply(lambda x: tuple(sorted(x)))

    # Group by column and strat names; these will be our matching groups
    counts = samples.groupby(["col_id", "strat_names"]).size().reset_index(name="count")

    app.console.print(f"Grouped {len(counts)} unique stratigraphic name groups.")

    counts["matches"] = counts.apply(
        lambda x: get_matched_unit(x.col_id, x.strat_names), axis=1
    )

    if verbose:
        for ix, row in counts.iterrows():
            print(f"{row['count']} samples in column {row['col_id']}")
            print("  " + ", ".join([format_name(i) for i in row["strat_names"]]))
            print("  " + ", ".join([format_name(i) for i in row["matches"]]))
        print()

    # Summarize the counts
    match = counts["strat_names"].apply(lambda x: len(x) > 0)
    print_counts("candidate stratigraphic name", counts[match], n_total)

    match = counts["matches"].notnull()
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


def get_matched_unit(col_id, strat_names):
    M = get_db()
    sql = """
    SELECT
      sn.id,
      sn.strat_name,
      rank,
      u.col_id,
      u.id unit_id,
      u.strat_name verbatim_strat_name
    FROM macrostrat.strat_names sn
    JOIN macrostrat.unit_strat_names usn ON sn.id = usn.strat_name_id
    JOIN macrostrat.units u ON usn.unit_id = u.id
    WHERE u.col_id = :col_id
      AND sn.strat_name ILIKE '%'|| :strat_name ||'%'
      OR '%' || sn.strat_name || '%' ILIKE :strat_name"""

    results = []
    for strat_name in strat_names:
        results = M.run_query(
            sql,
            params=dict(col_id=col_id, strat_name=strat_name.name),
        ).all()
        if len(results) > 0:
            break

    for result in results:
        rank = None
        try:
            rank = StratRank(result.rank.lower())
        except ValueError:
            pass
        return StratNameTextMatch(
            name=result.strat_name,
            rank=rank,
        )
    return None


def standardize_strat_column(df, column_name, add_suffix="", drop_original=True):
    if "strat_names" not in df.columns:
        df["strat_names"] = df.apply(lambda x: list(), axis=1)

    ix = df[column_name].notnull()
    for ix, row in df[ix].iterrows():
        names = clean_strat_name(row[column_name] + add_suffix)
        for name in names:
            row.strat_names.append(name)
    if drop_original:
        df.drop(columns=[column_name], inplace=True)


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
