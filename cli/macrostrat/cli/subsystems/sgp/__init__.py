"""
Subsystem for SGP matching
"""

from pydantic import BaseModel
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
from sqlalchemy.sql import text
from pandas import read_sql, Series
from enum import Enum

from rich.live import Live
from rich.table import Table

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


class MatchType(Enum):
    Concepts = "concepts"
    AdjacentCols = "adjacent-cols"
    ColumnUnits = "column-units"
    FootprintIndex = "footprint-index"


class MatchComparison(Enum):
    Exact = "exact"
    Included = "included"
    Bidirectional = "bidirectional"
    Fuzzy = "fuzzy"


@sgp.command(
    name="match-units",
)
def import_sgp_data(
    verbose: bool = False,
    sample: bool = False,
    match: list[MatchType] = None,
    # comparison: MatchComparison = MatchComparison.Included.value,
):
    M = get_db()

    # TODO: simplify this
    uri = M.engine.url.set(database="sgp")
    uri_ = str(uri).replace("***", uri.password)
    sgp_db = Database(uri_)

    # Get samples data frame from SGP database

    sql = here / "measurements-to-match.sql"

    samples = GeoDataFrame.from_postgis(
        text(sql.read_text()),
        sgp_db.engine.connect(),
        geom_col="geom",
        index_col="sample_id",
    )

    if sample:
        samples = samples.sample(1000)

    # Standardize text columns
    samples["source_text"] = samples.apply(merge_text, axis=1)
    samples.drop(
        columns=["member", "formation", "group", "verbatim_strat"], inplace=True
    )

    # Join samples to columns
    columns = get_columns_data_frame()
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
    _match = counts["strat_names"].apply(lambda x: len(x) > 0)
    print_counts(app.console, "candidate stratigraphic name", counts[_match], n_total)

    # Create an empty column for matched units
    counts["match_unit"] = None

    status = MatchStatus(
        success=0,
        done=0,
        total=n_total,
    )

    with Live(
        generate_table(status)
    ) as live, M.engine.connect() as conn:  # update 4 times a second to feel fluid
        for ix, row in counts.iterrows():
            _match = get_matched_unit(
                conn,
                row["col_id"],
                row["strat_names"],
                types=match,
                # comparison=comparison,
            )
            message = "[red bold]no match[/]"
            if _match is not None:
                counts.loc[ix, "match_unit"] = _match.unit_id
                message = "[green bold]" + _match.strat_name_clean + "[/]"
                message += f" [dim italic]{_match.basis}[/]"
            status.increment(row["count"], _match is not None)
            sep = ""
            if verbose or _match is None:
                sep = "\n"
                live.console.print(
                    f"[dim italic]{row.source_text}[/]{sep}→ {format_names(row.strat_names)}{sep}→ {message}"
                )
            if verbose or _match is None:
                live.console.print("[dim]- col_id", int(row.col_id))
                if _match is not None:
                    live.console.print("[dim]- unit_id", _match.unit_id)
                    live.console.print(
                        f"[dim]- ages", f"{_match.b_age:.1f}-{_match.t_age:.1f} Ma"
                    )
                live.console.print()
            live.update(generate_table(status))

        _match = counts["match_unit"].notnull()
        print_counts(live.console, "matched unit", counts[_match], n_total)


class MatchStatus(BaseModel):
    success: int
    done: int
    total: int

    @property
    def failed(self):
        return self.done - self.success

    def increment(self, count, success=True):
        self.done += count
        if success:
            self.success += count


def generate_table(status: MatchStatus):
    table = Table()
    table.add_column("Successful matches")
    table.add_column("Failed matches")
    table.add_column("Completion")

    if status.done == 0:
        return table

    table.add_row(
        f"[green]{status.success}[/green]",
        f"[red]{status.failed}[/red]",
        f"{status.success/status.done*100:.1f}%",
    )
    return table


def print_counts(console, category, subset, target):
    match_count = subset["count"].sum()
    console.print(
        f"{match_count} samples have at least one {category}.",
        style="green bold" if match_count == target else None,
    )
    if match_count < target:
        console.print(
            f"{target - match_count} samples have no {category}.",
            style="yellow",
        )


def format_names(strat_names):
    return ", ".join([format_name(i) for i in strat_names])


_column_unit_index = {}


def get_column_units(conn, col_id, types: list[MatchType] = None):
    """
    Get a unit that matches a given stratigraphic name
    """
    global _column_unit_index

    sql = Path(__file__).parent / "column-strat-names.sql"

    if col_id in _column_unit_index:
        return _column_unit_index[col_id]

    if types is None or len(types) == 0:
        types = [MatchType.FootprintIndex, MatchType.AdjacentCols]

    units_df = read_sql(
        text(sql.read_text()),
        conn,
        params=dict(
            col_id=col_id,
            use_concepts=MatchType.Concepts in types,
            use_adjacent_cols=MatchType.AdjacentCols in types,
            use_footprint_index=MatchType.FootprintIndex in types,
            use_column_units=MatchType.ColumnUnits in types,
        ),
        coerce_float=False,
    )

    units_df["strat_name_clean"] = units_df["strat_name"].apply(clean_strat_name_text)

    _column_unit_index[col_id] = units_df
    return units_df


def get_matched_unit(
    conn,
    col_id,
    strat_names,
    comparison=MatchComparison.Included,
    types: list[MatchType] = None,
):
    """
    Get a unit that matches a given stratigraphic name
    """

    units = get_column_units(conn, col_id, types=types)
    u1 = units[units.strat_name_clean != None]

    u1.sort_values(by="strat_name_clean", inplace=True)

    if comparison == MatchComparison.Fuzzy:
        raise NotImplementedError("Fuzzy matching not implemented")

    for strat_name in strat_names:
        # Try for an exact match with all strat names
        for ix, row in u1.iterrows():
            name = row["strat_name_clean"]
            if strat_name.name == name:
                return row

    if comparison == MatchComparison.Exact:
        return None

    for strat_name in strat_names:
        # Try for a "like" match, which might catch verbatim strat names better
        for ix, row in u1.iterrows():
            name = row["strat_name_clean"]
            if name is None:
                continue
            if name in strat_name.name:
                return row

    if comparison == MatchComparison.Included:
        return None

    for strat_name in strat_names:
        # Finally check that our cleaned strat name does not include the cleaned name as a subset
        for ix, row in u1.iterrows():
            name = row["strat_name_clean"]
            if name is None:
                continue
            if strat_name.name in name:
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
        if lvl in ["unknown", "uncertain", ""]:
            continue
        if lvl is not None:
            names.append(lvl + " " + level.capitalize())
    lvl = row.get("verbatim_strat", None)
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
