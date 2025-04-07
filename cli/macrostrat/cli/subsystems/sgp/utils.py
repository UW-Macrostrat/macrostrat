from pathlib import Path

from geopandas import GeoDataFrame
from macrostrat.database import Database
from pandas import DataFrame
from sqlalchemy.sql import text

from macrostrat.cli.database import get_db

_query_cache = {}


def stored_procedure(key: str):
    global _query_cache
    if key in _query_cache:
        return _query_cache[key]
    fn = Path(__file__).parent / "sql" / (key + ".sql")
    sql = text(fn.read_text())
    _query_cache[key] = sql
    return sql


def get_sgp_db():
    # TODO: simplify this
    from macrostrat.core.config import settings

    url = settings.get("sgp_database")
    if url is None:
        # Try to assemble SGP database URL for the current environment
        M = get_db()
        uri = M.engine.url.set(database="sgp")
        url = str(uri).replace("***", uri.password)
    return Database(url)


def get_sgp_samples(procedure):
    SGP = get_sgp_db()
    measurements_query = stored_procedure(procedure)
    samples = GeoDataFrame.from_postgis(
        measurements_query,
        SGP.engine.connect(),
        geom_col="geom",
        index_col="sample_id",
    )
    return samples


def print_match_status(console, df, match, noun="column"):
    n_total = len(df)
    n_too_many = counts[counts.index > 1].sum()
    n_matched = counts[1]
    n_not_matched = counts.get(0, 0)

    console.print(
        f"Matched {n_matched} of {n_total} samples to a {noun}.",
        style="green",
    )

    if n_too_many > 0:
        console.print(
            f"{n_too_many} samples have multiple matched {noun}s.", style="yellow"
        )
    if n_not_matched > 0:
        console.print(
            f"{n_not_matched} samples have no matched {noun}s.", style="yellow"
        )
    if n_too_many + n_not_matched == 0:
        console.print(f"All samples matched to a single {noun}s.", style="green")


def write_to_file(samples: DataFrame, out_file: Path):
    # Convert to a standard data frame
    samples.insert(0, "longitude", samples["geom"].x)
    samples.insert(1, "latitude", samples["geom"].y)
    samples.drop(columns=["geom"], inplace=True)
    samples = DataFrame(samples)

    # Write to file
    if out_file.suffix == ".csv":
        samples.to_csv(out_file)
    elif out_file.suffix == ".tsv":
        samples.to_csv(out_file, sep="\t")
    elif out_file.suffix == ".parquet":
        samples.to_parquet(out_file)
    elif out_file.suffix == ".feather":
        samples.to_feather(out_file)
    elif out_file.suffix == ".xlsx":
        samples.to_excel(out_file)
    else:
        raise ValueError(
            "Unsupported file format (use .tsv, .parquet, .xlsx, or .feather)"
        )
