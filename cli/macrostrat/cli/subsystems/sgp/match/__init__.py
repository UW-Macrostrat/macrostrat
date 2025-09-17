"""
Subsystem for SGP matching
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from geoalchemy2 import Geometry, WKBElement
from geopandas import GeoDataFrame, sjoin
from macrostrat.database import Database
from pandas import DataFrame, isna, read_sql
from pydantic import BaseModel
from rich.live import Live
from rich.table import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import text
from typer import Option

from macrostrat.cli.database import get_db
from macrostrat.core.console import err_console as console
from .clean_strat_name import (
    StratNameTextMatch,
    StratRank,
    clean_strat_name,
    clean_strat_name_text,
    format_name,
)
from ..utils import get_sgp_samples, stored_procedure, write_to_file, get_sgp_db

here = Path(__file__).parent


def get_columns_data_frame(db: Database):
    """Get all Macrostrat columns as a GeoDataFrame"""
    sql = """
        SELECT col_id, ST_SetSRID(ca.col_area, 4326) as col_area
        FROM macrostrat.col_areas ca
        JOIN macrostrat.cols c
          ON c.id = ca.col_id
        WHERE c.status_code = 'active'
    """
    gdf = GeoDataFrame.from_postgis(
        text(sql), db.engine.connect(), geom_col="col_area", index_col="col_id"
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


@dataclass
class DatabaseConfig:
    macrostrat: Database = None
    sgp: Database = None


def match_sgp_data_cmd(
    out_file: Path = Option(None, help="Output file to write results to"),
    verbose: bool = Option(False, help="Verbose output"),
    sample: int = Option(None, help="Number of random samples to process"),
    column: int = Option(None, help="Restrict to a single Macrostrat column ID"),
    match: list[MatchType] = Option(None, help="Types of matches to use"),
    reset: bool = Option(False, help="Reset the SGP matches table before writing"),
    only_macrostrat: bool = Option(
        False, help="Only match samples that have Macrostrat as the primary age"
    ),
    write: bool = Option(True, help="Write results to the database"),
):
    """Match SGP samples to Macrostrat units"""
    return match_sgp_data(
        out_file=out_file,
        verbose=verbose,
        sample=sample,
        column=column,
        match=match,
        reset=reset,
        only_macrostrat=only_macrostrat,
        write=write,
    )


def match_sgp_data(
    out_file: Path = None,
    *,
    verbose: bool = False,
    sample: int = None,
    column: int = None,
    match: list[MatchType] = None,
    reset: bool = False,
    only_macrostrat: bool = False,
    write: bool = False,
    databases: DatabaseConfig = None,
    # comparison: MatchComparison = MatchComparison.Included.value,
):
    """
    Match SGP samples to Macrostrat units (core function)
    """
    if databases is None:
        databases = DatabaseConfig(macrostrat=get_db(), sgp=get_sgp_db())

    db = databases

    samples = get_sgp_samples(db.sgp, "all-match-samples")
    if only_macrostrat:
        samples = samples[samples["match_set"] != "Age from other sources"]

    console.print(
        f"Got {len(samples)} samples from the SGP database.",
        style="green",
    )

    # Run a small sample for testing
    if sample is not None:
        samples = samples.sample(sample)

    # Standardize text columns
    samples["source_text"] = samples.apply(merge_text, axis=1)
    samples.drop(
        columns=["member", "formation", "group", "verbatim_strat"], inplace=True
    )

    console.print("\nMacrostrat columns", style="bold")

    # Join samples to columns
    columns = get_columns_data_frame(db.macrostrat)
    sample_locs = samples.drop(columns=[i for i in samples.columns if i != "geom"])

    join = sjoin(sample_locs, columns, how="left", op="intersects")
    grouped = join.groupby("sample_id")
    counts = grouped.size().value_counts()
    res = grouped.aggregate("first")
    res.rename(columns={"index_right": "col_id"}, inplace=True)
    res.drop(columns=["geom"], inplace=True)

    n_total = len(res)
    n_too_many = counts[counts.index > 1].sum()

    # get number with col_id
    n_matched = len(res[res["col_id"].notnull()])
    n_not_matched = len(res[res["col_id"].isnull()])

    console.print(
        f"Matched {n_matched} of {n_total} samples to a Macrostrat column.",
        style="green",
    )

    if n_too_many > 0:
        console.print(
            f"{n_too_many} samples have multiple matched columns.", style="yellow"
        )
    if n_not_matched > 0:
        console.print(
            f"{n_not_matched} samples have no matched columns.", style="yellow"
        )
    if n_too_many + n_not_matched == 0:
        console.print("All measurements matched to a single column.", style="green")

    # Augment the samples with the matched column
    samples = samples.join(res, on="sample_id", how="left")

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

    console.print("\nStratigraphic names", style="bold")

    console.print(f"Found {len(counts)} unique stratigraphic name groups.")

    if verbose:
        for ix, row in counts.iterrows():
            console.print(f"{row['count']} samples in column {row['col_id']}")
            console.print("  " + format_names(row["strat_names"]))
        console.print()

    # Summarize the counts
    _match = counts["strat_names"].apply(lambda x: len(x) > 0)

    print_counts(console, "candidate stratigraphic name", counts[_match], n_total)

    # Add empty columns for match information

    console.print("\nUnit matching", style="bold")

    type_list = join_items(
        [f"[underline]{v.value}[/underline]" for v in get_match_types(match)],
        sep=", ",
        last=" or ",
    )

    console.print(
        "Matching based on",
        type_list,
        "\n",
        style="dim",
    )

    status = MatchStatus(
        success=0,
        done=0,
        total=n_total,
    )

    # Create a data frame of matches with the same index as the counts
    matches = {}

    with Live(
        generate_table(status)
    ) as live, db.macrostrat.engine.connect() as conn:  # update 4 times a second to feel fluid
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
            # log_match_data(row, _match, verbose=verbose, console=live.console)
            live.update(generate_table(status))

    # Create a data frame of matches with the same index as the counts
    matches = DataFrame(matches).T
    # Rename columns

    if matches.empty:
        console.print("No matches found.")
        return None

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
    print_counts(console, "matched unit", counts[_match], n_total)

    # Complex statement that basically keeps the sample index while merging the counts
    # into that data frame.
    samples = (
        samples.reset_index()
        .merge(counts, on=["col_id", "source_text"], how="left")
        .set_index("sample_id")
    )

    samples["age_span_delta"] = (
        samples["match_age_span"].astype(float)
        - (samples["max_age"] - samples["min_age"])
    ).round(2)

    samples["mid_age_delta"] = (
        samples["match_mid_age"].astype(float) - samples["interpreted_age"]
    ).round(2)

    samples["strat_names"] = samples["strat_names"].apply(format_names, use_rich=False)

    if out_file is not None:
        # Convert field to be more suitable for export

        write_to_file(samples, out_file)

    if write:
        # Check if table exists
        if reset:
            db.macrostrat.engine.execute(
                text("TRUNCATE TABLE integrations.sgp_matches")
            )

        samples["geom"] = samples["geom"].apply(
            lambda x: x if isna(x) else WKBElement(x.wkb, srid=4326)
        )

        samples.to_sql(
            "sgp_matches",
            db.macrostrat.engine,
            if_exists="append",
            schema="integrations",
            method=postgres_upsert,
            chunksize=1000,
            dtype={"geom": Geometry("POINT", srid=4326)},
        )

    return samples


def log_match_data(row, _match, *, verbose=False, console=console):
    message = "[red bold]no match[/]"
    if _match is not None:
        message = "[green bold]" + _match.strat_name_clean + "[/]"
        message += f" [dim italic]{_match.basis}[/]"
        message += f" [dim italic]{_match.spatial_basis}[/]"
    if verbose or _match is None:
        sep = "\n"
        txt = row.source_text
        if txt == "":
            txt = "<empty string>"
        console.print(
            f"Text: [dim italic]{txt}[/]{sep}→ Matches: {format_names(row.strat_names)}{sep}→ {message}"
        )
    if verbose or _match is None:
        if isna(row.col_id):
            console.print("[dim]- No matched column.")
        else:
            console.print("[dim]- col_id", int(row.col_id))
        if _match is not None:
            console.print("[dim]- unit_id", _match.unit_id)
            console.print(f"[dim]- ages", f"{_match.b_age:.1f}-{_match.t_age:.1f} Ma")

        if row["n_samples"]:
            console.print(f"- {row['n_samples']} samples", style="dim")
        console.print()


def log_match_row(row, *, verbose=False, console=console):
    match = None
    if not isna(row["unit_id"]):
        match = row
    log_match_data(row, match, verbose=verbose, console=console)


def log_matches(verbose: bool = False):
    """Log SGP matches to the console"""
    M = get_db()

    # Get the matches
    matches = read_sql(
        stored_procedure("match-results"),
        M.engine,
    )

    if matches.empty:
        console.print("No matches found.")
        return

    for ix, row in matches.iterrows():
        log_match_row(row, verbose=verbose, console=console)


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

    if len(subset) == 0:
        console.print(f"No samples have any {category}.", style="yellow")
        return
    match_count = subset["count"].sum()
    console.print(
        f"{match_count} samples have one or more {category}.",
        style="green bold" if match_count == target else None,
    )
    if match_count < target:
        console.print(
            f"{target - match_count} samples have no {category}.",
            style="yellow",
        )
    console.print()


def format_names(strat_names, **kwargs):
    # Ignore nan values
    if isna(strat_names):
        return strat_names
    # if it's already a string, return it
    if isinstance(strat_names, str):
        return strat_names

    return ", ".join([format_name(i, **kwargs) for i in strat_names])


_column_unit_index = {}


def get_match_types(types: list[MatchType] | None) -> list[MatchType]:
    if types is None:
        return [
            MatchType.ColumnUnits,
            MatchType.Concepts,
            MatchType.FootprintIndex,
            MatchType.AdjacentCols,
            MatchType.Synonyms,
        ]
    return types


def get_column_units(conn, col_id, types: list[MatchType] = None):
    """
    Get a unit that matches a given stratigraphic name
    """
    global _column_unit_index

    if col_id in _column_unit_index:
        return _column_unit_index[col_id]

    types = get_match_types(types)

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
    u1 = units[units.strat_name_clean is not None]

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


def postgres_upsert(table, conn, keys, data_iter):
    # Get name of primary key constraint from DDL

    data = [dict(zip(keys, row)) for row in data_iter]

    insert_statement = insert(table.table).values(data)
    upsert_statement = insert_statement.on_conflict_do_update(
        # constraint=f"{table.table.name}_pkey",
        index_elements=["sample_id"],
        set_={c.key: c for c in insert_statement.excluded},
    )
    conn.execute(upsert_statement)


def join_items(items, sep=", ", last=" and "):
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    return sep.join(items[:-1]) + last + items[-1]
