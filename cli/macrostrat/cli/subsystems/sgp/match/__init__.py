"""
Subsystem for SGP matching
"""

from enum import Enum
from pathlib import Path

import IPython
from geopandas import GeoDataFrame, sjoin
from pandas import DataFrame, read_sql
from pydantic import BaseModel
from rich.live import Live
from rich.table import Table
from sqlalchemy.sql import text

from macrostrat.cli.database import get_db
from macrostrat.core import app

from ..utils import get_sgp_samples, stored_procedure, write_to_file
from .clean_strat_name import (
    StratNameTextMatch,
    StratRank,
    clean_strat_name,
    clean_strat_name_text,
    format_name,
)

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
    Synonyms = "synonyms"


class MatchComparison(Enum):
    Exact = "exact"
    Included = "included"
    Bidirectional = "bidirectional"
    Fuzzy = "fuzzy"


def import_sgp_data(
    out_file: Path = None,
    verbose: bool = False,
    sample: int = None,
    column: int = None,
    match: list[MatchType] = None,
    # comparison: MatchComparison = MatchComparison.Included.value,
):
    """
    Match SGP samples to Macrostrat units
    """
    M = get_db()

    samples = get_sgp_samples("initial-match-samples")

    # Run a small sample for testing
    if sample is not None:
        samples = samples.sample(sample)

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

    # If we have specified a single column, filter to that column
    if column is not None:
        samples = samples[samples["col_id"] == column]

    n_total = len(samples)

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
            app.console.print(f"{row['count']} samples in column {row['col_id']}")
            app.console.print("  " + format_names(row["strat_names"]))
        app.console.print()

    # Summarize the counts
    _match = counts["strat_names"].apply(lambda x: len(x) > 0)
    print_counts(app.console, "candidate stratigraphic name", counts[_match], n_total)

    # Add empty columns for match information

    status = MatchStatus(
        success=0,
        done=0,
        total=n_total,
    )

    # Create a data frame of matches with the same index as the counts
    matches = {}

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
            matches[ix] = _match
            status.increment(row["count"], _match is not None)
            log_match_data(row, _match, verbose=verbose, console=live.console)
            live.update(generate_table(status))

    # Create a data frame of matches with the same index as the counts
    matches = DataFrame(matches).T
    # Rename columns

    # Add interpreted age information by taking the midpoint ages
    ix = matches.columns.get_loc("max_age")
    matches.insert(ix + 1, "mid_age", (matches["min_age"] + matches["max_age"]) / 2)

    # Age spans
    matches.insert(ix + 2, "age_span", matches["max_age"] - matches["min_age"])

    matches.rename(
        columns={k: f"match_{k}" for k in matches.columns},
        inplace=True,
    )

    # Merge the matches with the counts
    counts = counts.join(matches, how="left")

    _match = counts["match_unit_id"].notnull()
    print_counts(live.console, "matched unit", counts[_match], n_total)

    # Complex statement that basically keeps the sample index while merging the counts
    # into that data frame.
    samples = (
        samples.reset_index()
        .merge(counts, on=["col_id", "source_text"])
        .set_index("sample_id")
    )

    samples["age_span_delta"] = (
        samples["match_age_span"].astype(float)
        - (samples["max_age"] - samples["min_age"])
    ).round(2)

    samples["mid_age_delta"] = (
        samples["match_mid_age"].astype(float) - samples["interpreted_age"]
    ).round(2)

    if out_file is not None:
        # Convert field to be more suitable for export
        samples["strat_names"] = samples["strat_names"].apply(
            format_names, use_rich=False
        )
        write_to_file(samples, out_file)
    else:
        IPython.embed()


def log_match_data(row, _match, *, verbose=False, console=app.console):
    message = "[red bold]no match[/]"
    if _match is not None:
        message = "[green bold]" + _match.strat_name_clean + "[/]"
        message += f" [dim italic]{_match.basis}[/]"
        message += f" [dim italic]{_match.spatial_basis}[/]"
    if verbose or _match is None:
        sep = "\n"
        console.print(
            f"[dim italic]{row.source_text}[/]{sep}→ {format_names(row.strat_names)}{sep}→ {message}"
        )
    if verbose or _match is None:
        console.print("[dim]- col_id", int(row.col_id))
        if _match is not None:
            console.print("[dim]- unit_id", _match.unit_id)
            console.print(f"[dim]- ages", f"{_match.b_age:.1f}-{_match.t_age:.1f} Ma")
        console.print()


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


def format_names(strat_names, **kwargs):
    return ", ".join([format_name(i, **kwargs) for i in strat_names])


_column_unit_index = {}


def get_column_units(conn, col_id, types: list[MatchType] = None):
    """
    Get a unit that matches a given stratigraphic name
    """
    global _column_unit_index

    if col_id in _column_unit_index:
        return _column_unit_index[col_id]

    if types is None or len(types) == 0:
        types = [
            MatchType.ColumnUnits,
            MatchType.Concepts,
            MatchType.FootprintIndex,
            MatchType.AdjacentCols,
            MatchType.Synonyms,
        ]

    units_df = read_sql(
        stored_procedure("column-strat-names"),
        conn,
        params=dict(
            col_id=col_id,
            use_concepts=MatchType.Concepts in types,
            use_synonyms=MatchType.Synonyms in types,
            use_adjacent_cols=MatchType.AdjacentCols in types,
            use_footprint_index=MatchType.FootprintIndex in types,
            use_column_units=MatchType.ColumnUnits in types,
        ),
        coerce_float=False,
    )

    # Insert column strat_name_clean after strat_name
    ix = units_df.columns.get_loc("strat_name")
    units_df.insert(
        ix + 1, "strat_name_clean", units_df["strat_name"].apply(clean_strat_name_text)
    )

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
    name_index = set()

    for name in names:
        out_name = clean_strat_name(name)

        for n1 in out_name:
            if n1.name in name_index:
                continue
            # Tracker for names
            name_index.add(n1.name)
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


def deduplicate_strat_names(samples):
    return list(set(samples))