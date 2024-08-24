"""
Subsystem for SGP matching
"""

from typer import Typer
from ...database import get_db
from macrostrat.core import app
from macrostrat.database import Database
from pathlib import Path
from rich import print
from rich.progress import Progress
from geopandas import GeoDataFrame, sjoin
from shapely.geometry import Point
from sqlalchemy.sql import text
from pandas import read_sql


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


@sgp.command(name="match-units")
def import_sgp_data():
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

    # Step through columns and try to match samples to units

    samples.groupby("col_id").apply(match_samples_to_column_units)


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
