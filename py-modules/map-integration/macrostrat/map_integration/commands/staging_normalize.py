import csv
import inspect
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
from psycopg2.sql import SQL, Identifier
from rich.console import Console
from rich.markup import escape
from rich.prompt import Prompt
from typer import Argument, Context, Exit, Option

from macrostrat.map_integration.commands.prepare_fields.utils import (
    LineworkTableUpdater,
    PointsTableUpdater,
    PolygonTableUpdater,
)
from macrostrat.map_integration.database import get_database
from macrostrat.map_integration.utils import IngestionCLI
from macrostrat.map_utils.slugs import slug_forms, staging_table

console = Console()

"""
Future subcommands to add
fill-null
rename-values
trim-whitespace
lowercase-column
coalesce-columns
"""

AGE_TERM_REMAP = {
    "pre-jurassic": "triassic",
    "pre-tertiary": "mesozoic",
    "paleoozoic": "paleozoic",
}

AGE_MODIFIER_REMAP = {
    "upper": "late",
    "lower": "early",
}

# udt_names Postgres treats as text for assignment purposes.
TEXTUAL_UDT_NAMES = {"text", "varchar", "bpchar", "name", "citext"}

# How many distinct matched-lith strings the fuzzy-match digest lists.
LITH_SUMMARY_LIMIT = 25

# ingest_process_tag value recorded when b_interval/t_interval remain unresolved.
AGES_NULL_TAG = "some ages null"

NON_LITHS = {
    "and",
    "or",
    "with",
    "of",
    "the",
    "a",
    "an",
    "to",
    "in",
    "on",
    "by",
    "for",
    "from",
    "as",
    "at",
    "late",
    "less",
}


@dataclass(frozen=True)
class TableTarget:
    """Immutable dataclass representing a fully-qualified database table target,
    identified by its schema and table name."""

    schema: str
    table: str

    @property
    def fq_identifier(self):
        """Returns an Identifier composed of (schema, table), suitable for safe interpolation into SQL queries."""
        return Identifier(self.schema, self.table)

    @property
    def layer(self) -> str:
        """polygons, lines or points, from the table's suffix."""
        return self.table.rsplit("_", 1)[-1]


def get_column_sql_type(target: TableTarget, column: str) -> str:
    """Return the SQL data type for a column on the target table."""
    db = get_database()
    row = db.run_query(
        """
        SELECT data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
          AND column_name = :column
        """,
        dict(schema=target.schema, table=target.table, column=column),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"Column '{column}' does not exist in {target.schema}.{target.table}"
        )

    # udt_name is useful for postgres-specific types like int4, bool, etc.
    return (row.udt_name or row.data_type or "").lower()


def append_ingest_comment(
    slug: str,
    comment: str,
    dry_run: bool = False,
):
    """Append a comment fragment to maps_metadata.ingest_process.comments for a
    slug, avoiding duplicate appends.
    """
    db = get_database()
    comment = comment.strip()
    if comment == "":
        raise ValueError("comment cannot be empty")
    if dry_run:
        console.print(
            f"[green]Dry run only:[/green] would append comment "
            f"[yellow]{comment}[/yellow] to maps_metadata.ingest_process for slug "
            f"[yellow]{slug}[/yellow]"
        )
        return
    db.run_sql(
        """
        UPDATE maps_metadata.ingest_process
        SET comments = CASE
            WHEN comments IS NULL OR trim(comments) = '' THEN :comment
            WHEN comments LIKE '%' || :comment || '%' THEN comments
            ELSE comments || ' ' || :comment
        END
        WHERE source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
        """,
        dict(
            slug=slug,
            comment=comment,
        ),
    )
    console.print(
        f"[green]Done:[/green] appended ingest_process comment for slug {slug}"
    )


def get_integer_preferred_fields_for_table(table: str) -> set[str]:
    """Returns the subset of preferred column names for the given table whose SQL types are integer-like (integer,
    bigint, serial, bigserial). Used to determine which destination columns require integer casting during
    column-copy operations."""
    preferred_fields = get_preferred_fields_for_table(table)
    integer_types = {"integer", "bigint", "serial", "bigserial"}

    out = set()
    for col_name, col_type in preferred_fields.items():
        normalized = col_type.strip().lower()
        if any(t in normalized for t in integer_types):
            out.add(col_name)

    return out


def validate_identifier(value: str, label: str) -> str:
    """Strips whitespace from a column identifier string and raises a ValueError if the result is empty.
    Returns the cleaned identifier on success."""
    value = value.strip()
    if value == "":
        raise ValueError(f"{label} cannot be empty")
    return value


def get_existing_columns(target: TableTarget) -> set[str]:
    """Queries information_schema to retrieve all column names currently present in the given table.
    Raises a ValueError if the table does not exist.
    Returns a set of column name strings."""
    db = get_database()
    table_exists = db.run_query(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_name = :table
        )
        """,
        dict(schema=target.schema, table=target.table),
    ).scalar()
    if not table_exists:
        raise ValueError(f"Table {target.schema}.{target.table} does not exist")
    cols = db.run_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
        """,
        dict(schema=target.schema, table=target.table),
    ).fetchall()
    return {row.column_name for row in cols}


def get_preferred_fields_for_table(table: str) -> dict[str, str]:
    """Infers the expected column specification (name -> SQL type) for a staging table based on its suffix: _points,
    _lines, or _polygons. Raises a ValueError if the table name does not match any known suffix.
    """
    if table.endswith("_points"):
        return PointsTableUpdater.column_spec
    if table.endswith("_lines"):
        return LineworkTableUpdater.column_spec
    if table.endswith("_polygons"):
        return PolygonTableUpdater.column_spec
    raise ValueError(
        "Could not infer table type from table name. "
        "Expected table to end with _points, _lines, or _polygons."
    )


def get_nonempty_columns_ending_with_e(target: TableTarget) -> list[str]:
    """Return all non-empty columns ending with 'e' ordered by ordinal_position ascending."""
    db = get_database()
    cols = db.run_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
          AND lower(column_name) ILIKE 'legend%e'
        ORDER BY ordinal_position
        """,
        dict(schema=target.schema, table=target.table),
    ).fetchall()

    out: list[str] = []
    for row in cols:
        col = row.column_name
        has_data = db.run_query(
            """
            SELECT EXISTS (
                SELECT 1
                FROM {table}
                WHERE {col} IS NOT NULL
                  AND trim({col}::text) <> ''
            )
            """,
            dict(
                table=target.fq_identifier,
                col=Identifier(col),
            ),
        ).scalar()
        if has_data:
            out.append(col)

    return out


def get_columns_between_non_age_and_second_last(
    target: TableTarget,
    non_age_col: str,
) -> tuple[str, list[str], str]:
    """Return (non_age_col, columns_between, second_last_col) for non-empty columns ending with 'e'."""
    non_age_col = validate_identifier(non_age_col, "non_age_col")
    e_cols = get_nonempty_columns_ending_with_e(target)

    if non_age_col not in e_cols:
        raise ValueError(
            f"Column '{non_age_col}' is not a non-empty column ending with 'e' "
            f"in {target.schema}.{target.table}"
        )

    if len(e_cols) < 2:
        raise ValueError(
            f"Need at least two non-empty columns ending with 'e' in "
            f"{target.schema}.{target.table}"
        )

    second_last_col = e_cols[-2]
    non_age_idx = e_cols.index(non_age_col)
    second_last_idx = e_cols.index(second_last_col)

    if non_age_idx > second_last_idx:
        columns_between = e_cols[second_last_idx + 1 : non_age_idx]
    else:
        columns_between = e_cols[non_age_idx + 1 : second_last_idx]

    return non_age_col, columns_between, second_last_col


def find_last_nonempty_column_ending_with_e(target: TableTarget) -> str:
    """Return the last column by ordinal position whose name ends with 'e'
    and which contains at least one nonblank value.
    """
    db = get_database()
    cols = db.run_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
          AND lower(column_name) ILIKE 'legend%e'
        ORDER BY ordinal_position DESC
        """,
        dict(schema=target.schema, table=target.table),
    ).fetchall()

    for row in cols:
        col = row.column_name
        has_data = db.run_query(
            """
            SELECT EXISTS (
                SELECT 1
                FROM {table}
                WHERE {col} IS NOT NULL
                  AND trim({col}::text) <> ''
            )
            """,
            dict(
                table=target.fq_identifier,
                col=Identifier(col),
            ),
        ).scalar()
        if has_data:
            return col
    raise ValueError(
        f"No non-empty column ending with 'e' found in {target.schema}.{target.table}"
    )


def tokenize_lith_text(value: str) -> list[str]:
    text = re.sub(r"[^A-Za-z0-9]+", " ", str(value)).strip().lower()
    if text == "":
        return []

    return [tok for tok in text.split() if tok and tok not in NON_LITHS]


def get_lith_reference_terms() -> tuple[set[str], set[str]]:
    """Build normalized lith and lith_att vocabularies separately."""
    db = get_database()

    lith_rows = db.run_query(
        """
        SELECT lith::text AS term
        FROM macrostrat.liths
        WHERE lith IS NOT NULL

        UNION

        SELECT lith_group::text AS term
        FROM macrostrat.liths
        WHERE lith_group IS NOT NULL

        UNION

        SELECT lith_type::text AS term
        FROM macrostrat.liths
        WHERE lith_type IS NOT NULL

        UNION

        SELECT lith_class::text AS term
        FROM macrostrat.liths
        WHERE lith_class IS NOT NULL
        """
    ).fetchall()

    att_rows = db.run_query(
        """
        SELECT lith_att::text AS term
        FROM macrostrat.lith_atts
        WHERE lith_att IS NOT NULL
        """
    ).fetchall()

    def normalize_terms(rows) -> set[str]:
        out = set()
        for row in rows:
            term = re.sub(r"\s+", " ", str(row.term)).strip().lower()
            if term != "":
                out.add(term)
        return out

    return frozenset(normalize_terms(lith_rows)), frozenset(normalize_terms(att_rows))


def best_fuzzy_match(
    token: str, reference_terms: set[str], min_ratio: float = 0.0
) -> tuple[Optional[str], float]:
    """Return the best matching reference term and its similarity ratio, or
    (None, 0.0) when none reaches `min_ratio`.

    Terms that cannot beat the best so far, or reach `min_ratio`, are skipped on
    the cheap upper bounds of their ratio (length alone, then `quick_ratio`)
    before the full comparison, which picks the same term as comparing all.
    """
    token = token.strip().lower()
    if token == "":
        return None, 0.0
    if token in reference_terms:
        return token, 1.0

    best_term = None
    best_ratio = 0.0
    n = len(token)
    for ref in reference_terms:
        floor = max(best_ratio, min_ratio)
        bound = 2.0 * min(n, len(ref)) / (n + len(ref))
        if bound < floor or (best_term is not None and bound <= best_ratio):
            continue
        matcher = SequenceMatcher(None, token, ref)
        quick = matcher.quick_ratio()
        if quick < floor or (best_term is not None and quick <= best_ratio):
            continue
        ratio = matcher.ratio()
        if ratio > best_ratio and ratio >= min_ratio:
            best_ratio = ratio
            best_term = ref

    return best_term, best_ratio


def lith_phrases(
    lith_terms: frozenset, att_terms: frozenset
) -> dict[tuple[str, ...], tuple[Optional[str], Optional[str]]]:
    """The terms of more than one word, keyed by their words as
    `tokenize_lith_text` splits text: ("reddish", "brown") -> ("reddish brown",
    None), ("quartz", "monzonite") -> (None, "quartz monzonite"). Matched
    exactly, not fuzzily. An att wins a tie, as in `match_lith_token`."""
    phrases = {}
    for terms, as_att in ((att_terms, True), (lith_terms, False)):
        for term in sorted(terms):
            words = tuple(tokenize_lith_text(term))
            if len(words) > 1:
                phrases.setdefault(words, (term, None) if as_att else (None, term))
    return phrases


@lru_cache(maxsize=None)
def match_lith_token(
    token: str, lith_terms: frozenset, att_terms: frozenset, threshold: float
) -> tuple[Optional[str], Optional[str]]:
    """(lith_att, None), (None, lith) or (None, None) for one word. A word
    recurs across a map's descriptions, and across maps, so each is matched
    once.

    A word of four letters or fewer matches only as written or as a plural
    (`dune` -> `dunes`). Fuzzily, nearly every one is wrong: `than` -> `tan`,
    `wash` -> `ash`, `tank` -> `tan`, `lack` -> `black`.
    """
    if len(token) <= 4:
        forms = [token, token + "s"] + ([token[:-1]] if token.endswith("s") else [])
        best_att = next((f for f in forms if f in att_terms), None)
        best_lith = next((f for f in forms if f in lith_terms), None)
        att_score = 1.0 if best_att else 0.0
        lith_score = 1.0 if best_lith else 0.0
    else:
        best_att, att_score = best_fuzzy_match(token, att_terms, threshold)
        best_lith, lith_score = best_fuzzy_match(token, lith_terms, threshold)
    # The better match, keeping whether it came from lith_atts or liths.
    if best_att is not None and att_score >= threshold and att_score >= lith_score:
        return best_att, None
    if best_lith is not None and lith_score >= threshold:
        return None, best_lith
    return None, None


def format_liths(lith_atts: dict[str, list[str]]) -> str:
    """Liths as the lexicon's lithology matcher shows them, each after its
    atts, which are separated by commas, and the liths by semicolons:
    "cross-bedded, fine sandstone; siltstone". The matcher reads this back to
    the same liths and atts."""
    return "; ".join(
        " ".join(filter(None, [", ".join(a), lith])) for lith, a in lith_atts.items()
    )


def calculate_lith_fuzzy_match_percentages(
    target: TableTarget,
    src_col: str | list[str],
    threshold: float = 0.9,
    limit: Optional[int] = None,
    dry_run: bool = False,
    verbose: bool = False,
):
    """Report fuzzy match percentages for tokens in src_col against the macrostrat
    lith/lith_att vocabularies.

    By default only a digest is printed: the distinct matched strings with row
    counts. Pass verbose=True for the per-row detail.

    src_col may be one column or a list of them. Several columns are concatenated
    per row before tokenizing, so a single pass sees every token -- calling this
    once per column would not work, because each call overwrites lith rather than
    adding to it.

    Every row with a match gets the matched liths and atts in its lith column;
    a row with none keeps its lith.
    """
    db = get_database()
    src_cols = [src_col] if isinstance(src_col, str) else list(src_col)
    src_cols = [validate_identifier(col, "source column") for col in src_cols]
    if not src_cols:
        raise ValueError("at least one source column is required")
    existing_cols = get_existing_columns(target)

    missing = [col for col in src_cols if col not in existing_cols]
    if missing:
        raise ValueError(
            f"Column(s) {', '.join(missing)} do not exist in "
            f"{target.schema}.{target.table}"
        )
    if "lith" not in existing_cols:
        raise ValueError(
            f"Destination column 'lith' does not exist in {target.schema}.{target.table}"
        )

    lith_terms, lith_att_terms = get_lith_reference_terms()

    limit_sql = ""
    params = {"table": target.fq_identifier}
    refs = []
    for i, col in enumerate(src_cols):
        params[f"c{i}"] = Identifier(col)
        refs.append(f"{{c{i}}}")
    if limit is not None:
        limit_sql = "LIMIT :limit"
        params["limit"] = limit

    # concat_ws skips nulls, so a row contributes whichever columns have text.
    # trim(NULL) is NULL and NULL <> '' is NULL, so the OR keeps only rows with
    # text in at least one column.
    value_expr = "concat_ws(' ', " + ", ".join(f"{ref}::text" for ref in refs) + ")"
    nonblank = " OR ".join(f"trim({ref}::text) <> ''" for ref in refs)

    rows = db.run_query(
        f"""
        SELECT _pkid, {value_expr} AS src_value
        FROM {{table}}
        WHERE ({nonblank})
          AND coalesce(omit, false) = false
        ORDER BY _pkid
        {limit_sql}
        """,
        params,
    ).fetchall()
    console.print(
        f"[blue]Evaluating lith fuzzy matches for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"using [yellow]{', '.join(src_cols)}[/yellow] across {len(rows)} row(s)"
    )
    total_rows = 0
    total_word_count = 0
    total_match_percent = 0.0
    updates: list[tuple[int, str]] = []
    # Descriptions repeat heavily across polygons, so the distinct set of matched
    # strings is a far shorter -- and more reviewable -- digest than one line per row.
    matched_counts = Counter()
    phrases = lith_phrases(lith_terms, lith_att_terms)
    longest = max(map(len, phrases), default=1)
    for row in rows:
        tokens = tokenize_lith_text(row.src_value)
        word_count = len(tokens)
        total_rows += 1
        total_word_count += word_count
        if not tokens:
            total_match_percent += 0.0
            matched_counts[""] += 1
            continue
        matched_count = 0
        # Each lith with its atts, in the order the text gives them. Text reads
        # `<att> <lith>`, as the column importer parses it, so atts belong to
        # the lith directly after them ("light, dark gray sandstone"), or with
        # none, directly before them ("sandstone, fine"). Atts next to no lith
        # describe a word Macrostrat lacks ("light orange") and are dropped,
        # not carried to a lith further on.
        lith_atts: dict[str, list[str]] = {}
        pending: list[str] = []
        before = None  # the lith directly before `pending`
        i = 0
        while i < len(tokens):
            # A term of several words ("reddish brown", "quartz monzonite",
            # "cross-bedded") as written, longest first; then the word alone.
            for n in range(min(longest, len(tokens) - i), 1, -1):
                if (phrase := phrases.get(tuple(tokens[i : i + n]))) is not None:
                    best_att, best_lith = phrase
                    break
            else:
                n = 1
                best_att, best_lith = match_lith_token(
                    tokens[i], lith_terms, lith_att_terms, threshold
                )
            i += n
            if best_att is not None:
                matched_count += n
                if best_att not in pending:
                    pending.append(best_att)
            elif best_lith is not None:
                matched_count += n
                atts = lith_atts.setdefault(best_lith, [])
                atts.extend(a for a in pending if a not in atts)
                pending, before = [], best_lith
            else:
                if before is not None:
                    lith_atts[before].extend(
                        a for a in pending if a not in lith_atts[before]
                    )
                pending, before = [], None
        if before is not None:
            lith_atts[before].extend(a for a in pending if a not in lith_atts[before])

        percent = 100.0 * matched_count / word_count
        total_match_percent += percent
        matched_string = format_liths(lith_atts)
        matched_counts[matched_string] += 1
        if verbose:
            value = re.sub(r"\s+", " ", str(row.src_value))[:70]
            console.print(
                f"_pkid={row._pkid} | words={word_count} | match={percent:.1f}% | "
                f"matched={matched_string} | value={value}"
            )

        if matched_string != "":
            updates.append((row._pkid, matched_string))

    if updates and not dry_run:
        # Two arrays, not a VALUES row per update: Postgres takes at most 65,535
        # bind parameters, which a large map's rows would pass.
        db.run_query(
            """
            UPDATE {table} AS t SET lith = v.lith
            FROM unnest(CAST(:ids AS bigint[]), CAST(:liths AS text[])) AS v(_pkid, lith)
            WHERE t._pkid = v._pkid
            """,
            dict(
                table=target.fq_identifier,
                ids=[pkid for pkid, _ in updates],
                liths=[lith for _, lith in updates],
            ),
        )
        db.session.commit()

        console.print(
            f"[green]Done:[/green] wrote matched lith strings into "
            f"[bold]lith[/bold] for {len(updates)} row(s)"
        )

    elif dry_run:
        console.print(
            f"[green]Dry run only; would write lith for {len(updates)} row(s)[/green]"
        )

    avg_words = (total_word_count / total_rows) if total_rows > 0 else 0.0
    avg_match_percent = (total_match_percent / total_rows) if total_rows > 0 else 0.0

    console.print(
        f"[green]Summary:[/green] "
        f"columns={', '.join(src_cols)} | rows={total_rows} | "
        f"avg_words={avg_words:.2f} | avg_match={avg_match_percent:.1f}% | "
        f"distinct matches={len(matched_counts)}"
    )
    for matched_string, count in matched_counts.most_common(LITH_SUMMARY_LIMIT):
        label = matched_string if matched_string else "[dim](no match)[/dim]"
        console.print(f"  {count:>6} rows  {label}")
    hidden = len(matched_counts) - LITH_SUMMARY_LIMIT
    if hidden > 0:
        console.print(f"  [dim]... and {hidden} more distinct match string(s)[/dim]")


def null_matching_value(
    target: TableTarget,
    column: str,
    value: str,
    dry_run: bool = False,
):
    """Sets cells in the specified column to NULL where the current value exactly
    matches the provided string. Validates that the column exists before executing.
    When dry_run is True, the operation is described but not executed.
    """
    db = get_database()
    column = validate_identifier(column, "column")
    existing_cols = get_existing_columns(target)

    if column not in existing_cols:
        raise ValueError(
            f"Column '{column}' does not exist in {target.schema}.{target.table}"
        )

    match_count = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {column}::text = :value
        """,
        dict(
            table=target.fq_identifier,
            column=Identifier(column),
            value=value,
        ),
    ).scalar()

    console.print(
        f"[blue]Preparing to set matching values to NULL in[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"column [yellow]{column}[/yellow] where value = [yellow]{value}[/yellow] "
        f"across {match_count} matching rows"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return

    db.run_sql(
        """
        UPDATE {table}
        SET {column} = NULL
        WHERE {column}::text = :value
        """,
        dict(
            table=target.fq_identifier,
            column=Identifier(column),
            value=value,
        ),
    )

    console.print(
        f"[green]Done:[/green] set matching values in {column} to NULL "
        f"in {target.schema}.{target.table}"
    )


def null_column_values(
    target: TableTarget,
    column: str,
    dry_run: bool = False,
):
    """Sets all values in the specified column to NULL for the target table.
    Validates that the column exists before executing. When dry_run is True,
    the operation is described but not executed.
    """
    db = get_database()
    column = validate_identifier(column, "column")
    existing_cols = get_existing_columns(target)

    if column not in existing_cols:
        raise ValueError(
            f"Column '{column}' does not exist in {target.schema}.{target.table}"
        )

    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[blue]Preparing to set all values to NULL in[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"column [yellow]{column}[/yellow] across {row_count} rows"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return

    db.run_sql(
        "UPDATE {table} SET {column} = NULL",
        dict(
            table=target.fq_identifier,
            column=Identifier(column),
        ),
    )

    console.print(
        f"[green]Done:[/green] set all values in {column} to NULL "
        f"in {target.schema}.{target.table}"
    )


def add_preferred_columns(
    target: TableTarget,
    dry_run: bool = False,
):
    """Adds any missing preferred standard columns to the target table using
    ALTER TABLE ... ADD COLUMN IF NOT EXISTS. Columns that already exist are skipped.
    When dry_run is True, intended changes are printed but no SQL is executed."""
    db = get_database()
    existing_cols = get_existing_columns(target)
    preferred_spec = get_preferred_fields_for_table(target.table)
    console.print(
        f"[blue]Checking preferred columns for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold]"
    )
    for col_name, col_type in preferred_spec.items():
        if col_name in existing_cols:
            console.print(
                f"[yellow]Skipping[/yellow] [bold]{col_name}[/bold]: already exists"
            )
            continue
        console.print(
            f"[blue]Adding[/blue] [bold]{col_name}[/bold] [dim]({col_type})[/dim]"
        )
        if dry_run:
            continue
        db.run_sql(
            "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {type}",
            dict(
                table=target.fq_identifier,
                column=Identifier(col_name),
                type=SQL(col_type),
            ),
        )
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
    else:
        console.print("[green]Done:[/green] preferred columns check/add complete")


def replace_value_with_column(
    target: TableTarget,
    src: str,
    dst: str,
    dst_val: str,
    dry_run: bool = False,
) -> int:
    """Replace a specific value in dst with the row-wise value from src.

    Example:
    - src=trend, dst=strike, dst_val=0
    - For rows where strike::text = '0', set strike = trend.

    Rules:
    - validates src and dst columns exist
    - only replaces rows where dst::text exactly matches dst_val
    - skips null/blank/unknown/none source values
    - returns count of rows still matching dst_val after the update
    """
    db = get_database()
    src = validate_identifier(src, "source column")
    dst = validate_identifier(dst, "destination column")
    existing_cols = get_existing_columns(target)

    if src not in existing_cols:
        raise ValueError(
            f"Source column '{src}' does not exist in {target.schema}.{target.table}"
        )

    if dst not in existing_cols:
        raise ValueError(
            f"Destination column '{dst}' does not exist in {target.schema}.{target.table}"
        )

    candidate_rows = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {dst}::text = :dst_val
          AND {src} IS NOT NULL
          AND trim({src}::text) <> ''
          AND lower(trim({src}::text)) <> 'unknown'
          AND lower(trim({src}::text)) <> 'none'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            dst=Identifier(dst),
            dst_val=dst_val,
        ),
    ).scalar()

    console.print(
        f"[blue]Preparing to replace[/blue] "
        f"[yellow]{dst}[/yellow] value [yellow]{dst_val}[/yellow] "
        f"with row-wise values from [yellow]{src}[/yellow] "
        f"in [bold]{target.schema}.{target.table}[/bold] "
        f"across {candidate_rows} candidate row(s)"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return candidate_rows

    db.run_sql(
        """
        UPDATE {table}
        SET {dst} = {src}
        WHERE {dst}::text = :dst_val
          AND {src} IS NOT NULL
          AND trim({src}::text) <> ''
          AND lower(trim({src}::text)) <> 'unknown'
          AND lower(trim({src}::text)) <> 'none'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            dst=Identifier(dst),
            dst_val=dst_val,
        ),
    )

    remaining_matches = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {dst}::text = :dst_val
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            dst=Identifier(dst),
            dst_val=dst_val,
        ),
    ).scalar()

    console.print(
        f"[green]Done:[/green] replaced [yellow]{dst} = {dst_val}[/yellow] "
        f"with row-wise values from [yellow]{src}[/yellow]. "
        f"Remaining matching {dst} rows: {remaining_matches}"
    )

    return remaining_matches


def remove_word_in_string(
    target: TableTarget,
    src: str,
    word: str,
    dry_run: bool = False,
) -> int:
    """Remove all occurrences of a word/string fragment from a text column.

    Example:
    - src=descrip
    - word='Unknown; '
    - 'Unknown; Unknown; Unit Boundary; Fault' -> 'Unit Boundary; Fault'

    Rules:
    - validates that src exists
    - updates src in place
    - skips NULL rows
    - removes all occurrences of word
    - trims leading/trailing whitespace after replacement
    - converts empty strings back to NULL
    - returns the number of rows still containing word after update
    """
    db = get_database()
    src = validate_identifier(src, "source column")
    existing_cols = get_existing_columns(target)

    if src not in existing_cols:
        raise ValueError(
            f"Column '{src}' does not exist in {target.schema}.{target.table}"
        )

    if word == "":
        raise ValueError("word cannot be empty")

    candidate_rows = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {src} IS NOT NULL
          AND {src}::text LIKE '%' || :word || '%'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            word=word,
        ),
    ).scalar()

    console.print(
        f"[blue]Preparing to remove[/blue] [yellow]{word}[/yellow] "
        f"from column [yellow]{src}[/yellow] in "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"across {candidate_rows} candidate row(s)"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return candidate_rows

    db.run_sql(
        """
        UPDATE {table}
        SET {src} = NULLIF(trim(replace({src}::text, :word, '')), '')
        WHERE {src} IS NOT NULL
          AND {src}::text LIKE '%' || :word || '%'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            word=word,
        ),
    )

    remaining_matches = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {src} IS NOT NULL
          AND {src}::text LIKE '%' || :word || '%'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            word=word,
        ),
    ).scalar()

    console.print(
        f"[green]Done:[/green] removed [yellow]{word}[/yellow] "
        f"from [yellow]{src}[/yellow]. "
        f"Remaining matching row(s): {remaining_matches}"
    )

    return remaining_matches


def replace_column_value(
    target: TableTarget,
    column: str,
    old_value: str,
    new_value: str,
    dry_run: bool = False,
):
    """Replace one value with another in a specified column.
    Lets PostgreSQL enforce type compatibility and surfaces a clean error if the
    replacement value is invalid for the target column.
    """
    db = get_database()
    column = validate_identifier(column, "column")
    existing_cols = get_existing_columns(target)

    if column not in existing_cols:
        raise ValueError(
            f"Column '{column}' does not exist in {target.schema}.{target.table}"
        )

    match_count = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {column}::text = :old_value
        """,
        dict(
            table=target.fq_identifier,
            column=Identifier(column),
            old_value=old_value,
        ),
    ).scalar()

    console.print(
        f"[blue]Preparing to replace values in[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"column [yellow]{column}[/yellow] "
        f"from [yellow]{old_value}[/yellow] to [yellow]{new_value}[/yellow] "
        f"across {match_count} matching rows"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return

    try:
        db.run_sql(
            """
            UPDATE {table}
            SET {column} = :new_value
            WHERE {column}::text = :old_value
            """,
            dict(
                table=target.fq_identifier,
                column=Identifier(column),
                old_value=old_value,
                new_value=new_value,
            ),
        )
    except Exception as e:
        raise ValueError(
            f"Could not replace values in column '{column}'. "
            f"PostgreSQL rejected the new value '{new_value}'. "
            f"Original error: {e}"
        ) from e

    console.print(
        f"[green]Done:[/green] replaced matching values in {column} "
        f"in {target.schema}.{target.table}"
    )


def merge_column_values(
    target: TableTarget,
    col_one: str,
    col_two: str,
    separator: str,
    dry_run: bool = False,
):
    """Merge values from col_two into col_one using a user-provided separator.

    Rules:
    - Skip col_two values that are null, blank, whitespace, 'unknown', or 'none'
    - Skip rows where col_one already contains the col_two value, so re-running a
      merge does not append the same text twice
    - If col_one is null/blank, set col_one = col_two
    - Otherwise set col_one = col_one || separator || col_two
    """
    db = get_database()
    col_one = validate_identifier(col_one, "first column")
    col_two = validate_identifier(col_two, "second column")
    existing_cols = get_existing_columns(target)

    if col_one not in existing_cols:
        console.print(
            f"[yellow]Skipping merge. Column '{col_one}' does not exist in {target.schema}.{target.table}[/yellow]"
        )
        return
    if col_two not in existing_cols:
        console.print(
            f"[yellow]Skipping merge. Column '{col_two}' does not exist in {target.schema}.{target.table}[/yellow]"
        )
        return
    row_count = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {col_two} IS NOT NULL
          AND trim({col_two}::text) <> ''
          AND lower(trim({col_two}::text)) <> 'unknown'
          AND lower(trim({col_two}::text)) <> 'none'
          AND ({col_one} IS NULL
               OR strpos({col_one}::text, trim({col_two}::text)) = 0)
        """,
        dict(
            table=target.fq_identifier,
            col_one=Identifier(col_one),
            col_two=Identifier(col_two),
        ),
    ).scalar()

    console.print(
        f"[blue]Preparing to merge[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"[yellow]{col_two}[/yellow] into [yellow]{col_one}[/yellow] "
        f"using separator [yellow]{separator}[/yellow] "
        f"across {row_count} candidate rows"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return

    try:
        db.run_sql(
            """
            UPDATE {table}
            SET {col_one} = CASE
                WHEN {col_one} IS NULL OR trim({col_one}::text) = '' THEN trim({col_two}::text)
                ELSE trim({col_one}::text) || :separator || trim({col_two}::text)
            END
            WHERE {col_two} IS NOT NULL
              AND trim({col_two}::text) <> ''
              AND lower(trim({col_two}::text)) <> 'unknown'
              AND lower(trim({col_two}::text)) <> 'none'
              AND ({col_one} IS NULL
                   OR strpos({col_one}::text, trim({col_two}::text)) = 0)
            """,
            dict(
                table=target.fq_identifier,
                col_one=Identifier(col_one),
                col_two=Identifier(col_two),
                separator=separator,
            ),
        )
    except Exception as e:
        raise ValueError(
            f"Could not merge column '{col_two}' into '{col_one}'. Original error: {e}"
        ) from e

    console.print(
        f"[green]Done:[/green] merged values from {col_two} into {col_one} "
        f"in {target.schema}.{target.table}"
    )


def unmerge_column_values(
    target: TableTarget,
    src: str,
    dst: str,
    separator: str,
    skip_missing: bool = False,
    overwrite: bool = False,
    keep_prefix: bool = False,
    allowed_values: Optional[list[str]] = None,
) -> Optional[int]:
    """Copy the part of `src` that follows `separator` into `dst`.

    The inverse of merge_column_values: 'Contact, Approximate' with separator ', '
    writes 'Approximate' into dst.

    Rules:
    - splits on the first occurrence of separator; rows without it are skipped
    - skips null/blank src values and extracted values that are blank
    - only fills null dst rows unless overwrite is True
    - when keep_prefix is True, src is reduced to the part before the separator
      ('Contact, Approximate' -> 'Contact'), otherwise src is left unchanged
    - when allowed_values is given, every distinct parsed value is reported and
      only case-insensitive matches are written; unmatched rows are left entirely
      alone, so src keeps its full value
    - returns the count of remaining null dst rows, or None when a column is
      absent and skip_missing is True (instead of raising)
    """
    db = get_database()
    src = validate_identifier(src, "src column")
    dst = validate_identifier(dst, "dst column")
    existing_cols = get_existing_columns(target)

    if separator == "":
        raise ValueError("separator cannot be empty")

    for label, col in (("Source", src), ("Destination", dst)):
        if col not in existing_cols:
            message = (
                f"{label} column '{col}' does not exist in "
                f"{target.schema}.{target.table}"
            )
            if not skip_missing:
                raise ValueError(message)
            console.print(
                f"[yellow]Skipping unmerge {src} -> {dst}:[/yellow] {message}"
            )
            return None

    # strpos is 1-based, so skipping past the separator lands on the remainder;
    # strpos = 0 means the separator is absent and the row is excluded below.
    tail = (
        "btrim(substr({src}::text, "
        "strpos({src}::text, :separator) + length(:separator)))"
    )
    prefix = (
        "nullif(btrim(substr({src}::text, 1, strpos({src}::text, :separator) - 1)), '')"
    )
    params = dict(
        table=target.fq_identifier,
        src=Identifier(src),
        dst=Identifier(dst),
        separator=separator,
    )

    # Parseable rows, before the allowed-value and null-dst restrictions.
    parsed_filter = f"""
        WHERE {{src}} IS NOT NULL
          AND strpos({{src}}::text, :separator) > 0
          AND {tail} <> ''
    """

    allowed_filter = ""
    if allowed_values is not None:
        cleaned = [value.strip() for value in allowed_values if value.strip() != ""]
        if not cleaned:
            raise ValueError("allowed_values cannot be empty")

        for i, value in enumerate(cleaned):
            params[f"allowed_{i}"] = value.lower()
        placeholders = ", ".join(f":allowed_{i}" for i in range(len(cleaned)))
        allowed_filter = f"AND lower({tail}) IN ({placeholders})"

        found = db.run_query(
            f"SELECT DISTINCT {tail} AS value FROM {{table}} {parsed_filter} ORDER BY value",
            params,
        ).fetchall()
        lowered = {value.lower() for value in cleaned}
        matched = [row.value for row in found if row.value.lower() in lowered]
        unmatched = [row.value for row in found if row.value.lower() not in lowered]

        console.print(
            f"[blue]Parsed from[/blue] [yellow]{src}[/yellow] in "
            f"[bold]{target.schema}.{target.table}[/bold]: "
            f"[green]{', '.join(matched) if matched else 'none'}[/green]"
        )
        if unmatched:
            console.print(
                f"  [yellow]not in allowed values, left unwritten:[/yellow] "
                f"{', '.join(unmatched)}"
            )

    row_filter = f"""
        {parsed_filter}
          {allowed_filter}
          {"" if overwrite else "AND {dst} IS NULL"}
    """

    candidate_rows = db.run_query(
        f"SELECT count(*) FROM {{table}} {row_filter}",
        params,
    ).scalar()

    console.print(
        f"[blue]Preparing to unmerge[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"[yellow]{src}[/yellow] after [yellow]{separator}[/yellow] "
        f"-> [yellow]{dst}[/yellow] across {candidate_rows} candidate row(s)"
    )

    # Both SET expressions read the pre-update row, so trimming src in the same
    # statement cannot clobber the value the dst expression is reading.
    set_clauses = [f"{{dst}} = {tail}"]
    if keep_prefix:
        set_clauses.append(f"{{src}} = {prefix}")

    db.run_sql(
        f"UPDATE {{table}} SET {', '.join(set_clauses)} {row_filter}",
        params,
    )

    remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {dst} IS NULL
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            dst=Identifier(dst),
        ),
    ).scalar()

    console.print(
        f"[green]Done:[/green] unmerged {src} into {dst} "
        f"in {target.schema}.{target.table}. "
        f"Remaining null {dst} rows: {remaining_nulls}"
    )
    return remaining_nulls


def get_distinct_preview_values_for_column(
    target: TableTarget,
    column: str,
    limit: int = 30,
) -> list[str]:
    """Return a small preview of distinct nonblank values from a column."""
    db = get_database()
    column = validate_identifier(column, "column")

    rows = db.run_query(
        """
        SELECT DISTINCT trim({column}::text) AS value
        FROM {table}
        WHERE {column} IS NOT NULL
          AND trim({column}::text) <> ''
          AND lower(trim({column}::text)) <> 'unknown'
          AND lower(trim({column}::text)) <> 'none'
          AND coalesce(omit, false) = false
        ORDER BY value
        LIMIT :limit
        """,
        dict(
            table=target.fq_identifier,
            column=Identifier(column),
            limit=limit,
        ),
    ).fetchall()

    return [row.value for row in rows if row.value is not None]


def merge_column_into_destination(
    target: TableTarget,
    src_col: str,
    dst_col: str,
    dry_run: bool = False,
) -> int:
    """
    Merge values from src_col into dst_col.

    Rules:
    - skip src values that are NULL, blank, whitespace, 'unknown', or 'none'
    - if dst_col is NULL/blank, set dst_col = src_col
    - otherwise set dst_col = dst_col || ', ' || src_col
    - return remaining null/blank destination rows
    """
    db = get_database()
    src_col = validate_identifier(src_col, "source column")
    dst_col = validate_identifier(dst_col, "destination column")
    existing_cols = get_existing_columns(target)

    if src_col not in existing_cols:
        raise ValueError(
            f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
        )
    if dst_col not in existing_cols:
        raise ValueError(
            f"Destination column '{dst_col}' does not exist in {target.schema}.{target.table}"
        )

    candidate_rows = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {src_col} IS NOT NULL
          AND trim({src_col}::text) <> ''
          AND lower(trim({src_col}::text)) <> 'unknown'
          AND lower(trim({src_col}::text)) <> 'none'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src_col=Identifier(src_col),
        ),
    ).scalar()

    console.print(
        f"[blue]Merging[/blue] [yellow]{src_col}[/yellow] into [yellow]{dst_col}[/yellow] "
        f"across {candidate_rows} candidate rows"
    )

    if dry_run:
        remaining_nulls = db.run_query(
            """
            SELECT count(*)
            FROM {table}
            WHERE ({dst_col} IS NULL OR trim({dst_col}::text) = '')
              AND coalesce(omit, false) = false
            """,
            dict(
                table=target.fq_identifier,
                dst_col=Identifier(dst_col),
            ),
        ).scalar()
        console.print("[green]Dry run only; no changes applied[/green]")
        return remaining_nulls

    db.run_sql(
        """
        UPDATE {table}
        SET {dst_col} = CASE
            WHEN {dst_col} IS NULL OR trim({dst_col}::text) = '' THEN trim({src_col}::text)
            ELSE trim({dst_col}::text) || ', ' || trim({src_col}::text)
        END
        WHERE {src_col} IS NOT NULL
          AND trim({src_col}::text) <> ''
          AND lower(trim({src_col}::text)) <> 'unknown'
          AND lower(trim({src_col}::text)) <> 'none'
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src_col=Identifier(src_col),
            dst_col=Identifier(dst_col),
        ),
    )

    remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE ({dst_col} IS NULL OR trim({dst_col}::text) = '')
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            dst_col=Identifier(dst_col),
        ),
    ).scalar()

    console.print(
        f"[green]Done:[/green] merged values from {src_col} into {dst_col}. "
        f"Remaining null {dst_col} rows: {remaining_nulls}"
    )
    return remaining_nulls


def copy_column_values(
    target: TableTarget,
    src: str,
    dst: str,
    skip_missing: bool = False,
    overwrite: bool = False,
) -> Optional[int]:
    """Copies values from column `src` into currently-null rows of column `dst`
    in the target table. Validates that both columns exist before executing.
    When overwrite is True, existing `dst` values are first set to NULL wherever
    `src` has a value, so `src` wins on every row it populates.
    Returns the count of remaining null destination rows, or None when a column is
    absent and skip_missing is True (instead of raising).
    """
    db = get_database()
    src = validate_identifier(src, "src column")
    dst = validate_identifier(dst, "dst column")
    column_types = get_column_types(target)

    for label, col in (("Source", src), ("Destination", dst)):
        if col not in column_types:
            message = (
                f"{label} column '{col}' does not exist in "
                f"{target.schema}.{target.table}"
            )
            if not skip_missing:
                raise ValueError(message)
            console.print(f"[yellow]Skipping copy {src} -> {dst}:[/yellow] {message}")
            return None

    # Legacy tables sometimes carry a preferred column at the wrong type (e.g. a
    # numeric `age` where the spec wants text). Postgres will not put text into a
    # numeric column, so widen the destination to text -- which is what the column
    # spec asks for anyway -- rather than skipping the copy.
    if column_types[src] in TEXTUAL_UDT_NAMES and (
        column_types[dst] not in TEXTUAL_UDT_NAMES
    ):
        cast_column_to_text(target, dst)

    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[blue]Preparing to copy[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"[yellow]{src}[/yellow] -> [yellow]{dst}[/yellow] "
        f"across {row_count} rows"
    )

    # One statement, not a null-out followed by a copy: run_sql commits per
    # statement, so a two-step overwrite that fails on the copy (e.g. a text ->
    # numeric type mismatch) would leave dst permanently nulled.
    dst_filter = "" if overwrite else "AND {dst} IS NULL"
    db.run_sql(
        f"""
        UPDATE {{table}}
        SET {{dst}} = {{src}}
        WHERE {{src}} IS NOT NULL
          {dst_filter}
        """,
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            dst=Identifier(dst),
        ),
    )

    remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {dst} IS NULL
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            dst=Identifier(dst),
        ),
    ).scalar()

    console.print(
        f"[green]Done:[/green] copied values from {src} to {dst} "
        f"in {target.schema}.{target.table}. "
        f"Remaining null {dst} rows: {remaining_nulls}"
    )
    return remaining_nulls


def cast_column_to_text(target: TableTarget, column: str) -> bool:
    """Convert a column to text in place, keeping existing values via ::text.

    Legacy source data sometimes lands a preferred column at the wrong type (e.g. a
    numeric `age` where the spec wants text). add_preferred_columns uses ADD COLUMN
    IF NOT EXISTS, so it never repairs the type. Returns True if a change was made.
    """
    db = get_database()
    column = validate_identifier(column, "column")
    column_types = get_column_types(target)

    if column not in column_types:
        return False
    if column_types[column] in TEXTUAL_UDT_NAMES:
        return False

    console.print(
        f"[blue]Casting[/blue] [bold]{target.schema}.{target.table}.{column}[/bold] "
        f"from [yellow]{column_types[column]}[/yellow] to [yellow]text[/yellow]"
    )
    db.run_sql(
        "ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text",
        dict(table=target.fq_identifier, column=Identifier(column)),
    )
    return True


def copy_first_available_column(
    target: TableTarget,
    srcs: list[str],
    dst: str,
    overwrite: bool = False,
) -> Optional[int]:
    """Fill `dst` from each column in `srcs` in turn, stopping as soon as no null
    `dst` rows remain. Source columns absent from the table are skipped, so a list
    may name alternatives that only some tables use.

    Returns the remaining null count, or None if no source column was present.
    """
    remaining = None
    for src in srcs:
        result = copy_column_values(
            target=target,
            src=src,
            dst=dst,
            skip_missing=True,
            # Only the first column that actually copies may overwrite; later
            # columns fill the nulls it left rather than clobbering its work.
            overwrite=overwrite and remaining is None,
        )
        if result is None:
            continue
        remaining = result
        if remaining == 0:
            break

    return remaining


def update_ingest_status(
    slug: str,
    state: str,
    dry_run: bool = False,
):
    """Update maps_metadata.ingest_process.state for a slug."""
    db = get_database()
    state = state.strip()
    if state == "":
        raise ValueError("state cannot be empty")

    match_count = db.run_query(
        """
        SELECT count(*)
        FROM maps_metadata.ingest_process
        WHERE source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
        """,
        dict(slug=slug),
    ).scalar()
    console.print(
        f"[blue]Preparing to update ingest status for[/blue] "
        f"[yellow]{slug}[/yellow] "
        f"to state [yellow]{state}[/yellow] "
        f"across {match_count} matching rows"
    )
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return
    db.run_sql(
        """
        UPDATE maps_metadata.ingest_process
        SET state = :state
        WHERE source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
        """,
        dict(slug=slug, state=state),
    )

    db.run_sql(
        """
    UPDATE maps_metadata.ingest_process
    SET comments = 'metadata manually processed; polygons processed; lines processed; points processed;'
    WHERE source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
    """,
        dict(slug=slug, state=state),
    )
    console.print(f"[green]Done:[/green] updated ingest_process state for slug {slug}")


def copy_preferred_column_values_interactive(
    target: TableTarget,
    dry_run: bool = False,
):
    """Interactively prompts the user to map existing source columns into each preferred destination column for the
    target table. For integer-typed destination columns, the source value is cast to integer with NULL handling.
    When dry_run is True, prompts are shown and mappings are printed but no SQL is executed.
    """
    db = get_database()
    preferred_fields = get_preferred_fields_for_table(target.table)
    existing_cols = get_existing_columns(target)
    integer_dest_fields = get_integer_preferred_fields_for_table(target.table)

    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()
    console.print(
        f"[blue]Preparing interactive preferred-field mapping for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"across {row_count} rows"
    )
    console.print(f"[dim]Available columns:[/dim] {', '.join(sorted(existing_cols))}")
    for dst in preferred_fields:
        src = Prompt.ask(
            f"Map source column to preferred destination column [bold]{dst}[/bold] "
            f"(press Enter to skip)",
            default="",
            show_default=False,
        ).strip()
        if src == "":
            console.print(f"[yellow]Skipping[/yellow] destination [bold]{dst}[/bold]")
            continue
        if src not in existing_cols:
            console.print(
                f"[yellow]Skipping[/yellow] [bold]{src}[/bold] -> [bold]{dst}[/bold]: "
                f"source column does not exist"
            )
            continue
        if dst not in existing_cols:
            console.print(
                f"[yellow]Skipping[/yellow] [bold]{src}[/bold] -> [bold]{dst}[/bold]: "
                f"destination column does not exist"
            )
            continue
        console.print(
            f"[blue]Mapping[/blue] [yellow]{src}[/yellow] -> [yellow]{dst}[/yellow]"
        )
        if dry_run:
            continue
        if dst in integer_dest_fields:
            db.run_sql(
                """
                UPDATE {table}
                SET {dst} = CASE
                    WHEN {src} IS NULL THEN NULL
                    WHEN trim({src}::text) = '' THEN NULL
                    ELSE ({src}::text)::integer
                END
                """,
                dict(
                    table=target.fq_identifier,
                    src=Identifier(src),
                    dst=Identifier(dst),
                ),
            )
        else:
            db.run_sql(
                "UPDATE {table} SET {dst} = {src}",
                dict(
                    table=target.fq_identifier,
                    src=Identifier(src),
                    dst=Identifier(dst),
                ),
            )
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
    else:
        console.print("[green]Done:[/green] interactive preferred-field copy complete")


METADATA_FIELDS = [
    "name",
    "url",
    "ref_title",
    "authors",
    "ref_year",
    "ref_source",
    "isbn_doi",
    "license",
    "scale_denominator",
    "keywords",
    "language",
    "description",
]


def parse_metadata_value(field: str, raw_value: str):
    """Parses and coerces a raw string metadata value for a given field. Returns None for empty strings,
    an int for scale_denominator, a list of strings for keywords, and the stripped string for all other fields.
    """
    raw_value = raw_value.strip()
    if raw_value == "":
        return None
    if field == "scale_denominator":
        return int(raw_value)
    if field == "keywords":
        # comma-separated input -> text[]
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    return raw_value


# __________________________PROCESS METADATA VIA CSV OR INTERACTIVELY__________________________________
def is_blank_metadata_value(value) -> bool:
    """Return True if a CSV value should be treated as missing and skipped."""
    if value is None:
        return True

    # pandas-style NaN safety if a float sneaks in
    if isinstance(value, float) and math.isnan(value):
        return True

    text = str(value).strip()
    if text == "":
        return True

    if text.lower() in {"nan", "null", "none"}:
        return True

    return False


def parse_metadata_csv_value(field: str, raw_value):
    """
    Parse a metadata CSV value into the format expected by maps.sources.
    Returns None for blank values.
    """
    if is_blank_metadata_value(raw_value):
        return None

    raw_text = str(raw_value).strip()

    if field == "scale_denominator":
        return int(raw_text)

    if field == "keywords":
        # support either semicolon-separated or comma-separated values
        if ";" in raw_text:
            parts = [item.strip() for item in raw_text.split(";") if item.strip()]
        else:
            parts = [item.strip() for item in raw_text.split(",") if item.strip()]
        return parts

    return raw_text


def get_source_row_for_slug(slug: str):
    """Look up a maps.sources row by slug."""
    db = get_database()
    row = db.run_query(
        """
        SELECT source_id, slug
        FROM maps.sources
        WHERE slug = :slug
        """,
        dict(slug=slug),
    ).fetchone()

    if row is None:
        return None

    return row


def process_metadata_csv(
    csv_path: Path,
    dry_run: bool = False,
):
    """
    Read metadata rows from a CSV file and update maps.sources by slug.

    Rules:
    - slug is required
    - blank/null CSV values are skipped and do not overwrite DB values
    - rows with unknown slugs are skipped
    """
    db = get_database()

    if not csv_path.is_file():
        raise ValueError(f"Metadata CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header row: {csv_path}")

        missing_required = {"slug"} - set(reader.fieldnames)
        if missing_required:
            raise ValueError(
                f"CSV missing required column(s): {', '.join(sorted(missing_required))}"
            )

        rows = list(reader)

    console.print(
        f"[blue]Processing metadata CSV:[/blue] [bold]{csv_path}[/bold] "
        f"with {len(rows)} row(s)"
    )

    updated_count = 0
    skipped_missing_slug = 0
    skipped_unknown_slug = 0
    skipped_empty_updates = 0

    for i, row in enumerate(rows, start=1):
        slug = str(row.get("slug", "")).strip()

        if slug == "":
            skipped_missing_slug += 1
            console.print(f"[yellow]Skipping row {i}:[/yellow] missing slug")
            continue

        source_row = get_source_row_for_slug(slug)
        if source_row is None:
            skipped_unknown_slug += 1
            console.print(
                f"[yellow]Skipping row {i}:[/yellow] slug not found in maps.sources: "
                f"[bold]{slug}[/bold]"
            )
            continue

        updates = {}
        for field in METADATA_FIELDS:
            if field not in row:
                continue

            try:
                parsed = parse_metadata_csv_value(field, row[field])
            except Exception as e:
                console.print(
                    f"[yellow]Skipping field[/yellow] [bold]{field}[/bold] "
                    f"for slug [bold]{slug}[/bold]: invalid value {row[field]!r} ({e})"
                )
                continue

            if parsed is None:
                continue

            updates[field] = parsed

        if not updates:
            skipped_empty_updates += 1
            console.print(
                f"[yellow]Skipping row {i}:[/yellow] no non-empty metadata values for "
                f"[bold]{slug}[/bold]"
            )
            continue

        console.print(
            f"[blue]Prepared metadata update[/blue] for [bold]{slug}[/bold]: "
            f"{', '.join(sorted(updates.keys()))}"
        )

        if dry_run:
            continue

        assignments = [f"{field} = :{field}" for field in updates.keys()]
        params = {"source_id": source_row.source_id, **updates}

        sql = f"""
            UPDATE maps.sources
            SET {", ".join(assignments)}
            WHERE source_id = :source_id
        """
        db.run_sql(sql, params)
        updated_count += 1

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")

    console.print(
        "[green]Done:[/green] "
        f"updated={updated_count}, "
        f"missing_slug={skipped_missing_slug}, "
        f"unknown_slug={skipped_unknown_slug}, "
        f"empty_updates={skipped_empty_updates}"
    )


def _has_ingest_process_tag(db, slug: str, tag: str) -> bool:
    """True if this slug's ingest_process row already carries the tag."""
    return bool(
        db.run_query(
            """
            SELECT 1
            FROM maps_metadata.ingest_process_tag t
            JOIN maps_metadata.ingest_process i ON i.source_id = t.source_id
            WHERE i.source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
              AND t.tag = :tag
            """,
            dict(slug=slug, tag=tag),
        ).scalar()
    )


def add_ingest_process_tag(slug: str, tag: str, dry_run: bool = False):
    """Add a maps_metadata.ingest_process_tag row for a slug, ignoring duplicates.

    The insert joins through ingest_process to resolve the id, and pk_tag makes
    the ON CONFLICT a no-op on re-runs.
    """
    db = get_database()
    slug = (slug or "").strip()
    tag = (tag or "").strip()

    if slug == "":
        raise ValueError("slug cannot be empty")
    if tag == "":
        raise ValueError("tag cannot be empty")

    if dry_run:
        console.print(
            f"[green]Dry run only:[/green] would tag slug [yellow]{slug}[/yellow] "
            f"with [yellow]{tag}[/yellow]"
        )
        return

    if _has_ingest_process_tag(db, slug, tag):
        console.print(f"[dim]{slug} is already tagged {tag}; nothing to do[/dim]")
        return

    db.run_sql(
        """
        INSERT INTO maps_metadata.ingest_process_tag (source_id, tag)
        SELECT i.source_id, :tag
        FROM maps_metadata.ingest_process i
        WHERE i.source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
        ON CONFLICT DO NOTHING
        """,
        dict(slug=slug, tag=tag),
    )

    if _has_ingest_process_tag(db, slug, tag):
        console.print(
            f"[green]Tagged[/green] [yellow]{slug}[/yellow] with [yellow]{tag}[/yellow]"
        )
    else:
        console.print(
            f"[yellow]No ingest_process row for slug {slug}; tag not added[/yellow]"
        )


def remove_ingest_process_tag(slug: str, tag: str, dry_run: bool = False):
    """Delete a maps_metadata.ingest_process_tag row for a slug, if it is present.

    The inverse of add_ingest_process_tag: safe to call when the tag is absent, so
    callers can keep a tag in sync with a condition without checking first.
    """
    db = get_database()
    slug = (slug or "").strip()
    tag = (tag or "").strip()

    if slug == "":
        raise ValueError("slug cannot be empty")
    if tag == "":
        raise ValueError("tag cannot be empty")

    if dry_run:
        console.print(
            f"[green]Dry run only:[/green] would remove tag [yellow]{tag}[/yellow] "
            f"from slug [yellow]{slug}[/yellow]"
        )
        return

    if not _has_ingest_process_tag(db, slug, tag):
        return

    db.run_sql(
        """
        DELETE FROM maps_metadata.ingest_process_tag t
        USING maps_metadata.ingest_process i
        WHERE t.source_id = i.source_id
          AND i.source_id = (SELECT source_id FROM maps.sources WHERE slug = :slug)
          AND t.tag = :tag
        """,
        dict(slug=slug, tag=tag),
    )

    console.print(
        f"[green]Removed tag[/green] [yellow]{tag}[/yellow] "
        f"from [yellow]{slug}[/yellow]"
    )


def add_metadata_interactive(
    slug: str,
    dry_run: bool = False,
):
    """Interactively prompts the user to enter values for each metadata field in METADATA_FIELDS, then applies
    them as an UPDATE to the slug's maps.sources row. When dry_run is True, the prepared updates are printed
    but not written to the database."""
    db = get_database()
    source_row = get_source_row_for_slug(slug)
    console.print(
        f"[blue]Editing metadata for[/blue] [bold]maps.sources[/bold] "
        f"[yellow]{slug}[/yellow] (source_id={source_row.source_id})"
    )
    updates = {}
    for field in METADATA_FIELDS:
        raw_value = Prompt.ask(
            f"Enter value for metadata field [bold]{field}[/bold] "
            f"(press Enter to skip)",
            default="",
            show_default=False,
        )
        if raw_value.strip() == "":
            console.print(f"[yellow]Skipping[/yellow] [bold]{field}[/bold]")
            continue
        try:
            updates[field] = parse_metadata_value(field, raw_value)
        except ValueError:
            console.print(
                f"[red]Invalid value for[/red] [bold]{field}[/bold]. Skipping."
            )
            continue
    if not updates:
        console.print("[yellow]No metadata fields provided; nothing to update[/yellow]")
        return
    console.print("[blue]Prepared updates:[/blue]")
    for key, value in updates.items():
        console.print(f"- {key} = {value}")
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return
    assignments = []
    params = {"source_id": source_row.source_id}
    for field, value in updates.items():
        if field == "keywords":
            assignments.append(f"{field} = :{field}")
            params[field] = value
        else:
            assignments.append(f"{field} = :{field}")
            params[field] = value
    sql = f"""
        UPDATE maps.sources
        SET {", ".join(assignments)}
        WHERE source_id = :source_id
    """
    db.run_sql(sql, params)
    console.print("[green]Done:[/green] metadata updated")


# ________________CALCULATE AGES/LINE TYPES/POINT TYPES FUNCTIONS___________________________________________
#: How much of a description `review_ages` shows.
AGE_REVIEW_DESCRIPTION_CHARS = 600


def review_ages(db, target: TableTarget, dry_run: bool = False) -> None:
    """Ask for the age of each map unit whose polygons lack b_interval or
    t_interval, and set both from the answer, and `age` to the answer as typed.

    Polygons are asked about once per distinct name, descrip and age, most
    polygons first. An answer is read as the GeMS ingest reads an age
    (`lookup_and_validate_age`): "Late Pleistocene", "Miocene to Pliocene",
    "middle to late Pleistocene"; or interval ids, "23" or "23 to 40", whose
    names go into `age` ("Cenomanian to Rupelian"). `omit` sets omit = true on
    the unit's polygons instead, for unmapped or unnamed ones. Each unit is
    shown as its first polygon's whole row, and written and committed once
    confirmed, so stopping keeps what is done.
    """
    from ..utils.gems_utils import AGE_ALIASES, lookup_and_validate_age
    from ..utils.ingestion_utils import get_age_interval_df

    existing = get_existing_columns(target)
    missing = {"_pkid", "b_interval", "t_interval"} - existing
    if missing:
        raise ValueError(
            f"No {', '.join(sorted(missing))} in {target.schema}.{target.table}; "
            "run add-preferred-columns first"
        )
    shown = {
        c: Identifier(c) if c in existing else SQL("NULL")
        for c in ("name", "descrip", "age", "omit")
    }
    units = db.run_query(
        """
        SELECT {name}::text AS name, {descrip}::text AS descrip, {age}::text AS age,
            b_interval::text AS b_interval, t_interval::text AS t_interval,
            array_agg(_pkid ORDER BY _pkid) AS ids
        FROM {table}
        WHERE (b_interval IS NULL OR t_interval IS NULL)
          AND {omit} IS NOT TRUE
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY count(*) DESC, 1, 2
        """,
        dict(table=target.fq_identifier, **shown),
    ).all()
    n_polygons = sum(len(u.ids) for u in units)
    console.print(
        f"[blue]{n_polygons} polygon(s) in {len(units)} unit(s) lack an interval[/blue]"
    )
    if not units:
        return

    intervals = get_age_interval_df(db)
    by_id = {
        int(r.id): (r.interval_name, r.age_bottom, r.age_top)
        for r in intervals.itertuples()
    }
    lookup = {str(r.interval_name).lower(): int(r.id) for r in intervals.itertuples()}
    for alias, name in AGE_ALIASES.items():
        if name in lookup:
            lookup.setdefault(alias, lookup[name])
    ages = {i: (bottom, top) for i, (_, bottom, top) in by_id.items()}

    def label(interval) -> str:
        if interval in (None, ""):
            return "[dim]-[/dim]"
        name, bottom, top = by_id.get(int(interval), ("?", None, None))
        return f"{name} [dim]({interval}; {bottom}-{top} Ma)[/dim]"

    def resolve(answer: str):
        ids = re.fullmatch(r"\s*(\d+)\s*(?:(?:to|-)\s*(\d+)\s*)?", answer)
        if ids:
            found = [int(i) for i in ids.groups() if i is not None]
            if any(i not in by_id for i in found):
                return None
            # The older interval is the bottom one.
            found.sort(key=lambda i: -by_id[i][1])
            return found[0], found[-1]
        # "middle to late Pleistocene": each qualifier takes the shared epoch.
        shared = re.fullmatch(
            r"\s*(early|middle|late|lower|upper)\s*(?:to|-)\s*"
            r"(early|middle|late|lower|upper)\s+(.+?)\s*",
            answer,
            re.I,
        )
        if shared:
            first, second, epoch = shared.groups()
            answer = f"{first} {epoch} to {second} {epoch}"
        b, t = lookup_and_validate_age(answer, lookup, ages)
        if pd.isna(b) or pd.isna(t):
            return None
        return int(b), int(t)

    # Every column but the geometry, as text, for showing a polygon's row.
    shown_columns = [
        c
        for c, udt in get_column_types(target).items()
        if udt not in ("geometry", "geography")
    ]
    row_sql = ", ".join(f"{{c{i}}}::text" for i in range(len(shown_columns)))
    row_params = {f"c{i}": Identifier(c) for i, c in enumerate(shown_columns)}
    width = max(map(len, shown_columns))

    def show_row(pkid: int) -> None:
        values = db.run_query(
            f"SELECT {row_sql} FROM {{table}} WHERE _pkid = :pkid",
            dict(table=target.fq_identifier, pkid=pkid, **row_params),
        ).one()
        for column, value in zip(shown_columns, values):
            if column in ("b_interval", "t_interval"):
                value = label(value)
            elif value is None or value.strip() == "":
                value = "[dim]-[/dim]"
            else:
                value = re.sub(r"\s+", " ", value).strip()
                if len(value) > AGE_REVIEW_DESCRIPTION_CHARS:
                    value = value[:AGE_REVIEW_DESCRIPTION_CHARS] + "..."
                value = escape(value)
            console.print(f"  [cyan]{column:<{width}}[/cyan]  {value}")

    console.print(
        "Type each unit's age, or interval ids (23, 23 to 40), or omit. "
        "[dim]Enter skips a unit, q ends this map, Ctrl-C stops.[/dim]"
    )
    applied = omitted = 0
    for position, unit in enumerate(units, start=1):
        more = ", first shown" if len(unit.ids) > 1 else ""
        console.print(
            f"\n[bold]({position}/{len(units)})[/bold] {len(unit.ids)} polygon(s){more}"
        )
        show_row(unit.ids[0])
        while True:
            answer = Prompt.ask("  Age", default="", show_default=False).strip()
            if answer == "" or answer.lower() == "q":
                break
            if answer.lower() == "omit":
                if "omit" not in existing:
                    console.print(
                        "  [red]No omit column; run add-preferred-columns[/red]"
                    )
                    continue
                prompt = f"  Omit these {len(unit.ids)} polygon(s)?"
                if Prompt.ask(prompt, choices=["y", "n"], default="y") == "y":
                    break
                continue
            found = resolve(answer)
            if found is None:
                console.print(f"  [red]No interval matches '{answer}'[/red]")
                continue
            b, t = found
            age = answer
            if re.fullmatch(r"[\d\s-]+|\s*\d+\s*to\s*\d+\s*", answer):
                age = by_id[b][0] if b == t else f"{by_id[b][0]} to {by_id[t][0]}"
            console.print(f"  b_interval -> {label(b)}\n  t_interval -> {label(t)}")
            if "age" in existing:
                console.print(f"  age        -> {age}")
            if Prompt.ask("  Apply?", choices=["y", "n"], default="y") == "y":
                break
        if answer.lower() == "q":
            break
        if answer == "":
            continue
        if dry_run:
            console.print("  [yellow]Dry run; not written[/yellow]")
            continue
        if answer.lower() == "omit":
            db.run_query(
                "UPDATE {table} SET omit = true WHERE _pkid = ANY(CAST(:ids AS bigint[]))",
                dict(table=target.fq_identifier, ids=list(unit.ids)),
            )
            db.session.commit()
            omitted += len(unit.ids)
            continue
        db.run_query(
            """
            UPDATE {table} SET b_interval = :b, t_interval = :t {set_age}
            WHERE _pkid = ANY(CAST(:ids AS bigint[]))
            """,
            dict(
                table=target.fq_identifier,
                set_age=SQL(", age = :age" if "age" in existing else ""),
                b=b,
                t=t,
                age=age,
                ids=list(unit.ids),
            ),
        )
        db.session.commit()
        applied += len(unit.ids)
    console.print(
        f"\n[green]{applied} polygon(s) given an age and intervals, "
        f"{omitted} omitted[/green]"
    )


def copy_point_type_from_column(
    target: TableTarget,
    src_col: str,
    dry_run: bool = False,
) -> int:
    """Maps values from a source column into the point_type column by fuzzy-matching
    (case-insensitive, trimmed) against canonical point_type values in maps.points.
    Writes the matched integer maps.points.id into the destination point_type column.
    If src_col is point_type itself, all rows are remapped in place; otherwise only
    currently-null rows are filled. Returns the count of remaining null point_type rows.
    """
    db = get_database()
    src_col = validate_identifier(src_col, "source column")
    existing_cols = get_existing_columns(target)
    if src_col not in existing_cols:
        raise ValueError(
            f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
        )
    if "point_type" not in existing_cols:
        raise ValueError(
            f"Destination column 'point_type' does not exist in {target.schema}.{target.table}"
        )

    row_count = db.run_query(
        "SELECT count(*) FROM {table} ",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[blue]Mapping point types for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"from [yellow]{src_col}[/yellow] across {row_count} rows"
    )

    if dry_run:
        remaining_nulls = db.run_query(
            "SELECT count(*) FROM {table} WHERE point_type IS NULL AND coalesce(omit, false) = false",
            dict(table=target.fq_identifier),
        ).scalar()
        console.print("[green]Dry run only; no changes applied[/green]")
        return remaining_nulls

    if src_col == "point_type":
        db.run_sql(
            """
            WITH point_lookup AS (
                SELECT DISTINCT ON (lower(trim(point_type::text)))
                    lower(trim(point_type::text)) AS type_key,
                    point_type AS mapped_value
                FROM maps.point_type
                ORDER BY lower(trim(point_type::text)), point_type
            ),
            mapped AS (
                SELECT
                    t._pkid,
                    pl.mapped_value
                FROM {table} AS t
                LEFT JOIN point_lookup AS pl
                    ON lower(trim(nullif(t.point_type::text, ''))) = pl.type_key
            )
            UPDATE {table} AS t
            SET point_type = mapped.mapped_value
            FROM mapped
            WHERE t._pkid = mapped._pkid
            """,
            dict(table=target.fq_identifier),
        )
    else:
        db.run_sql(
            """
            WITH point_lookup AS (
                SELECT DISTINCT ON (lower(trim(point_type::text)))
                    lower(trim(point_type::text)) AS type_key,
                    point_type AS mapped_value
                FROM maps.point_type
                ORDER BY lower(trim(point_type::text)), point_type
            )
            UPDATE {table} AS t
            SET point_type = pl.mapped_value
            FROM point_lookup AS pl
            WHERE t.point_type IS NULL
              AND lower(trim(nullif(t.{src_col}::text, ''))) = pl.type_key
            """,
            dict(
                table=target.fq_identifier,
                src_col=Identifier(src_col),
            ),
        )

    remaining_nulls = db.run_query(
        "SELECT count(*) FROM {table} WHERE point_type IS NULL AND coalesce(omit, false) = false",
        dict(table=target.fq_identifier),
    ).scalar()
    console.print(
        f"[green]Done:[/green] mapped canonical point_type values from {src_col}. "
        f"Remaining null point_type rows: {remaining_nulls}"
    )
    return remaining_nulls


def copy_line_type_from_column(
    target: TableTarget,
    src_col: str,
    dry_run: bool = False,
) -> int:
    """Maps values from a source column into the type column by fuzzy-matching
    (case-insensitive, trimmed) against canonical type values in maps.lines.
    Writes the matched integer maps.lines.id into the destination type column.
    If src_col is type itself, all rows are remapped in place; otherwise only
    currently-null rows are filled. Returns the count of remaining null type rows."""
    db = get_database()
    src_col = validate_identifier(src_col, "source column")
    existing_cols = get_existing_columns(target)
    if src_col not in existing_cols:
        raise ValueError(
            f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
        )
    if "type" not in existing_cols:
        raise ValueError(
            f"Destination column 'type' does not exist in {target.schema}.{target.table}"
        )
    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()
    console.print(
        f"[blue]Mapping line types for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"from [yellow]{src_col}[/yellow] across {row_count} rows"
    )
    if dry_run:
        remaining_nulls = db.run_query(
            "SELECT count(*) FROM {table} WHERE type IS NULL AND coalesce(omit, false) = false",
            dict(table=target.fq_identifier),
        ).scalar()
        console.print("[green]Dry run only; no changes applied[/green]")
        return remaining_nulls
    if src_col == "type":
        db.run_sql(
            """
            WITH line_lookup AS (
                SELECT DISTINCT ON (lower(trim(line_type::text)))
                    lower(trim(line_type::text)) AS type_key,
                    line_type AS mapped_value
                FROM maps.line_type
                ORDER BY lower(trim(line_type::text)), line_type
            ),
            mapped AS (
                SELECT
                    t._pkid,
                    ll.mapped_value
                FROM {table} AS t
                LEFT JOIN line_lookup AS ll
                    ON lower(trim(nullif(t.type::text, ''))) = ll.type_key
            )
            UPDATE {table} AS t
            SET type = mapped.mapped_value
            FROM mapped
            WHERE t._pkid = mapped._pkid
            """,
            dict(table=target.fq_identifier),
        )
    else:
        db.run_sql(
            """
            WITH line_lookup AS (
                SELECT DISTINCT ON (lower(trim(line_type::text)))
                    lower(trim(line_type::text)) AS type_key,
                    line_type AS mapped_value
                FROM maps.line_type
                ORDER BY lower(trim(line_type::text)), line_type
            )
            UPDATE {table} AS t
            SET type = ll.mapped_value
            FROM line_lookup AS ll
            WHERE t.type IS NULL
              AND lower(trim(nullif(t.{src_col}::text, ''))) = ll.type_key
            """,
            dict(
                table=target.fq_identifier,
                src_col=Identifier(src_col),
            ),
        )
    remaining_nulls = db.run_query(
        "SELECT count(*) FROM {table} WHERE type IS NULL AND coalesce(omit, false) = false",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[green]Done:[/green] mapped canonical type values from {src_col}. "
        f"Remaining null type rows: {remaining_nulls}"
    )
    return remaining_nulls


def normalize_age_text(value: Optional[str]) -> Optional[str]:
    # is_blank_metadata_value also catches float NaN, which pandas substitutes for
    # NULL, and the literal string 'nan' that str(NaN) would otherwise produce.
    if is_blank_metadata_value(value):
        return None
    text = str(value).strip()
    if text == "":
        return None
    # remove "(?)", including with extra spaces: "( ? )"
    text = re.sub(r"\(\s*\?\s*\)", "", text, flags=re.IGNORECASE)
    # remove.g. "Jurassic (201.3-145 Ma)"
    text = re.sub(r"\s*\([^)]*ma[^)]*\)\s*$", "", text, flags=re.IGNORECASE)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text or None


def remap_age_term(term: Optional[str]) -> Optional[str]:
    # Guard against non-str input: pandas can hand a float NaN straight through an
    # .apply() chain, and 'nan is None' is False.
    if is_blank_metadata_value(term):
        return None

    term = str(term).strip().lower()
    term = AGE_TERM_REMAP.get(term, term)

    parts = term.split()
    if parts and parts[0] in AGE_MODIFIER_REMAP:
        parts[0] = AGE_MODIFIER_REMAP[parts[0]]
        term = " ".join(parts)

    return term


def get_age_lookup_candidates(term: Optional[str]) -> list[str]:
    """
    Return candidate interval names in priority order.

    Example:
    upper jurassic -> late jurassic -> jurassic
    lower cretaceous -> early cretaceous -> cretaceous
    pre-tertiary -> mesozoic
    """
    term = remap_age_term(term)
    if term is None:
        return []
    candidates = [term]
    parts = term.split()
    if len(parts) >= 2 and parts[0] in {"early", "middle", "late"}:
        candidates.append(" ".join(parts[1:]))
    # de-duplicate while preserving order
    out = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


def resolve_interval_id(
    term: Optional[str], interval_map: dict[str, int]
) -> Optional[int]:
    """
    Resolve an interval ID using ordered lookup candidates.

    Example:
    - "upper jurassic" becomes candidates ["late jurassic", "jurassic"]
    - returns late jurassic ID if present
    - otherwise returns jurassic ID if present
    """
    for candidate in get_age_lookup_candidates(term):
        if candidate in interval_map:
            return interval_map[candidate]
    return None


def parse_age_range(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = normalize_age_text(value)
    if text is None:
        return None, None
    text = remap_age_term(text)
    if " to " in text:
        left, right = text.split(" to ", 1)
        return remap_age_term(left), remap_age_term(right)
    if " and " in text:
        left, right = text.split(" and ", 1)
        return remap_age_term(left), remap_age_term(right)
    if "-" in text and not text.startswith("pre-"):
        left, right = text.split("-", 1)
        return remap_age_term(left), remap_age_term(right)
    return remap_age_term(text), remap_age_term(text)


# Preference order, not a filter: any qualifying column can be used, but when
# several qualify the earliest name here wins.
ORIG_ID_CANDIDATES = [
    "mapunitpolys_id",
    "descriptionofmapunits_id",
    "descriptionsourceid",
    "global_id",
    "contactsandfaults_id",
    "globalid",
    "orientationpoints_id",
]

# Accepted certainty values, matched case-insensitively. Seeded from the Arizona
# linework 'Type' column; extend as new values turn up rather than letting
# unrecognized text through.
LINE_CERTAINTY_VALUES = [
    "Accurate",
    "Approximate",
    "Concealed",
    "nature uncertain",
]

INTEGER_TEXT_PATTERN = "^-?[0-9]+$"

# Columns macrostrat manages itself; never useful as an original-id source.
ORIG_ID_MANAGED_COLUMNS = {
    "_pkid",
    "orig_id",
    "source_id",
    "omit",
    "description",
    "descrip",
}

# Only these types are worth testing. Keeps geometry (and other large or
# uncastable columns) out of the scan entirely.
ORIG_ID_SCANNABLE_TYPES = {
    "int2",
    "int4",
    "int8",
    "numeric",
    "text",
    "varchar",
    "bpchar",
}


def orig_id_preference(col: str) -> int:
    """Rank a column name against ORIG_ID_CANDIDATES; unlisted names sort last."""
    if col in ORIG_ID_CANDIDATES:
        return ORIG_ID_CANDIDATES.index(col)
    return len(ORIG_ID_CANDIDATES)


def get_column_types(target: TableTarget) -> dict[str, str]:
    """Return {column_name: udt_name} for the target table, in ordinal order.
    Raises a ValueError if the table does not exist."""
    db = get_database()
    rows = db.run_query(
        """
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
        ORDER BY ordinal_position
        """,
        dict(schema=target.schema, table=target.table),
    ).fetchall()

    if not rows:
        raise ValueError(f"Table {target.schema}.{target.table} does not exist")

    return {row.column_name: row.udt_name for row in rows}


def find_orig_id_candidates(
    target: TableTarget,
    columns: Optional[list[str]] = None,
) -> list[str]:
    """Return every column usable as an orig_id source, preserving the order of
    `columns` (or ordinal order when discovering them).

    A column qualifies only if, across all non-omitted rows, its values are
    non-null, nonblank, integer-castable, and unique. All columns are evaluated in
    a single aggregate query regardless of how many there are.
    """
    db = get_database()
    column_types = get_column_types(target)

    if columns is None:
        cols = [
            col
            for col, udt in column_types.items()
            if udt in ORIG_ID_SCANNABLE_TYPES and col not in ORIG_ID_MANAGED_COLUMNS
        ]
    else:
        cols = [col for col in columns if col in column_types]

    if not cols:
        return []

    params = {"table": target.fq_identifier}
    checks = []
    for i, col in enumerate(cols):
        params[f"c{i}"] = Identifier(col)
        # trim(NULL) is NULL and NULL ~ pattern is NULL, so the filter also
        # excludes null and blank rows; the CASE keeps the cast from ever
        # evaluating on a non-numeric row.
        text = f"trim({{c{i}}}::text)"
        checks.append(
            f"count(*) FILTER (WHERE {text} ~ '{INTEGER_TEXT_PATTERN}') AS valid_{i}, "
            f"count(DISTINCT CASE WHEN {text} ~ '{INTEGER_TEXT_PATTERN}' "
            f"THEN ({text})::integer END) AS distinct_{i}"
        )

    # Tables that have not been through add-preferred-columns yet have no omit.
    row_filter = "WHERE coalesce(omit, false) = false" if "omit" in column_types else ""

    stats = db.run_query(
        f"""
        SELECT count(*) AS total_rows, {", ".join(checks)}
        FROM {{table}}
        {row_filter}
        """,
        params,
    ).fetchone()

    if stats.total_rows == 0:
        return []

    return [
        col
        for i, col in enumerate(cols)
        if getattr(stats, f"valid_{i}") == stats.total_rows
        and getattr(stats, f"distinct_{i}") == stats.total_rows
    ]


def prompt_for_orig_id_column(
    target: TableTarget,
    valid: list[str],
    has_omit: bool = True,
) -> Optional[str]:
    """Show a sample of each qualifying column and ask which to copy into orig_id.
    Returns the chosen column, or None if the user skips this table.
    """
    db = get_database()

    params = {"table": target.fq_identifier}
    selects = []
    for i, col in enumerate(valid):
        params[f"c{i}"] = Identifier(col)
        selects.append(f"{{c{i}}}::text AS v{i}")

    row_filter = "WHERE coalesce(omit, false) = false" if has_omit else ""
    rows = db.run_query(
        f"""
        SELECT {", ".join(selects)}
        FROM {{table}}
        {row_filter}
        LIMIT 5
        """,
        params,
    ).fetchall()

    console.print(
        f"[blue]{len(valid)} orig_id candidates in[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold]"
    )
    for i, col in enumerate(valid):
        sample = ", ".join(str(getattr(row, f"v{i}")) for row in rows)
        console.print(f"  [yellow]{col}[/yellow]: [dim]{sample}[/dim]")

    choice = Prompt.ask(
        "Column to copy into orig_id (press Enter to skip)",
        choices=valid,
        default="",
        show_default=False,
        show_choices=False,
    )
    if choice == "":
        console.print(
            f"[yellow]Skipping[/yellow] orig_id for "
            f"[bold]{target.schema}.{target.table}[/bold]"
        )
        return None
    return choice


def copy_orig_id_from_candidates(
    target: TableTarget,
    candidates: Optional[list[str]] = None,
    dry_run: bool = False,
    interactive: bool = False,
) -> Optional[str]:
    """Copy a usable column into orig_id; return its name or None.

    With no explicit candidates, every scannable column on the table is tested and
    ORIG_ID_CANDIDATES breaks ties. Explicit candidates are tried in list order.
    When interactive is True and more than one column qualifies, the user picks
    which one to use; a single qualifier is copied without prompting.
    """
    db = get_database()
    column_types = get_column_types(target)

    if "orig_id" not in column_types:
        raise ValueError(
            f"Destination column 'orig_id' does not exist in {target.schema}.{target.table}"
        )

    valid = find_orig_id_candidates(target, columns=candidates)
    if not valid:
        console.print(
            f"[yellow]No valid orig_id source column found in[/yellow] "
            f"[bold]{target.schema}.{target.table}[/bold]"
        )
        return None

    if interactive and len(valid) > 1:
        col = prompt_for_orig_id_column(target, valid, has_omit="omit" in column_types)
        if col is None:
            return None
    else:
        # Explicit candidates already arrive in preference order; discovered
        # columns are in ordinal order, so prefer the conventional id names.
        col = valid[0] if candidates else min(valid, key=orig_id_preference)

    others = [c for c in valid if c != col]
    console.print(
        f"[blue]Copying[/blue] [yellow]{col}[/yellow] -> [yellow]orig_id[/yellow] "
        f"in [bold]{target.schema}.{target.table}[/bold]"
        + (f" [dim](also qualified: {', '.join(others)})[/dim]" if others else "")
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return col

    db.run_sql(
        """
        UPDATE {table}
        SET orig_id = (trim({src_col}::text))::integer
        WHERE coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src_col=Identifier(col),
        ),
    )

    console.print(
        f"[green]Done:[/green] copied values from {col} to orig_id "
        f"in {target.schema}.{target.table}"
    )
    return col


#: Column names `calculate_orig_id` takes for an id: `objectid`, `fid`,
#: `mapunitpolys_id`, a coverage's `tsn_geo-id` and `tsn_geo#`. A column must
#: be named as one, since `symbol` or `label` can be unique by chance.
ORIG_ID_NAME = re.compile(r".*(id|#)$")

#: Id-named columns that do not identify a feature: an ArcGIS representation's
#: symbol rule.
ORIG_ID_NOT_IDS = {"ruleid"}


def calculate_orig_id(db, target: TableTarget, dry_run: bool = False) -> None:
    """Give every feature of a table an orig_id: the map's own id where a column
    has one per feature, and otherwise 1, 2, 3, ... in `_pkid` order.

    An id column must be named as one (`ORIG_ID_NAME`) and, like `copy-orig-id`
    requires, hold a unique integer on every row not omitted;
    `ORIG_ID_CANDIDATES`, then `objectid`, are preferred. An orig_id that
    already meets that test is kept. Numbering covers omitted rows too, so
    un-omitting one leaves no gap.
    """
    try:
        column_types = get_column_types(target)
    except ValueError:
        console.print("[dim]No table[/dim]")
        return
    missing = {"_pkid", "orig_id"} - column_types.keys()
    if missing:
        raise ValueError(
            f"No {', '.join(sorted(missing))} in {target.schema}.{target.table}; "
            "run add-preferred-columns first"
        )
    if find_orig_id_candidates(target, columns=["orig_id"]):
        console.print("[dim]orig_id is already a unique id; kept[/dim]")
        return

    named = [
        col
        for col, udt in column_types.items()
        if udt in ORIG_ID_SCANNABLE_TYPES
        and col not in ORIG_ID_MANAGED_COLUMNS | ORIG_ID_NOT_IDS
        and ORIG_ID_NAME.fullmatch(col)
    ]
    valid = find_orig_id_candidates(target, columns=named) if named else []
    if valid:
        col = min(
            valid,
            key=lambda c: (orig_id_preference(c), c != "objectid", valid.index(c)),
        )
        others = [c for c in valid if c != col]
        console.print(
            f"Copying [yellow]{col}[/yellow] -> orig_id"
            + (f" [dim](also unique: {', '.join(others)})[/dim]" if others else "")
        )
        if dry_run:
            console.print("[green]Dry run only; no changes applied[/green]")
            return
        copy_orig_id_from_candidates(target, candidates=[col])
        return

    n = db.run_query(
        "SELECT count(*) FROM {table}", dict(table=target.fq_identifier)
    ).scalar()
    console.print(f"No unique id column; numbering {n} feature(s) 1-{n} by _pkid")
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return
    db.run_query(
        """
        UPDATE {table} t SET orig_id = n.id
        FROM (SELECT _pkid, row_number() OVER (ORDER BY _pkid) AS id FROM {table}) n
        WHERE t._pkid = n._pkid
        """,
        dict(table=target.fq_identifier),
    )
    db.session.commit()


def copy_age_columns(
    target: TableTarget,
    older_col: str,
    newer_col: str,
    dry_run: bool = False,
) -> int:
    """Copy age text from source columns into b_interval and t_interval using
    pandas for normalization/parsing and one final bulk SQL update.

    Age-column population rule:
    - First calculate candidate b_interval/t_interval matches.
    - Calculate the percent of candidate rows that matched an interval.
    - Only copy raw older_col values into age if match_percent > 50%.
    - Only copy age for rows that actually produced interval candidates.
    - Remaining null age rows can be filled by later copy-age passes.
    """
    db = get_database()
    older_col = validate_identifier(older_col, "older column")
    newer_col = validate_identifier(newer_col, "newer column")
    existing_cols = get_existing_columns(target)

    if older_col not in existing_cols:
        raise ValueError(
            f"Column '{older_col}' does not exist in {target.schema}.{target.table}"
        )
    if newer_col not in existing_cols:
        raise ValueError(
            f"Column '{newer_col}' does not exist in {target.schema}.{target.table}"
        )
    missing_required = {"b_interval", "t_interval"} - existing_cols
    if missing_required:
        raise ValueError(
            f"Missing required destination columns in {target.schema}.{target.table}: "
            f"{', '.join(sorted(missing_required))}. "
            f"Run add-preferred-columns first."
        )
    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()
    console.print(
        f"[blue]Copying age columns for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"using older=[yellow]{older_col}[/yellow], "
        f"newer=[yellow]{newer_col}[/yellow] across {row_count} rows"
    )

    rows = db.run_query(
        """
        SELECT _pkid, {older_col} AS older_raw, {newer_col} AS newer_raw
        FROM {table}
        WHERE (b_interval IS NULL OR t_interval IS NULL)
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            older_col=Identifier(older_col),
            newer_col=Identifier(newer_col),
        ),
    ).fetchall()
    if not rows:
        return 0
    df = pd.DataFrame(
        [
            {
                "_pkid": row._pkid,
                "older_raw": row.older_raw,
                "newer_raw": row.newer_raw,
            }
            for row in rows
        ]
    )
    df["older_norm"] = df["older_raw"].apply(normalize_age_text).apply(remap_age_term)
    df["newer_norm"] = df["newer_raw"].apply(normalize_age_text).apply(remap_age_term)
    parsed = df["older_raw"].apply(parse_age_range)
    df["older_left"] = parsed.apply(lambda x: x[0])
    df["older_right"] = parsed.apply(lambda x: x[1])

    interval_rows = db.run_query(
        """
        SELECT lower(trim(interval_name)) AS interval_name, min(id) AS id
        FROM macrostrat.intervals
        GROUP BY 1
        """
    ).fetchall()

    interval_map = {
        row.interval_name: row.id
        for row in interval_rows
        if row.interval_name is not None
    }
    df["older_id"] = df["older_norm"].apply(
        lambda x: resolve_interval_id(x, interval_map)
    )
    df["newer_id"] = df["newer_norm"].apply(
        lambda x: resolve_interval_id(x, interval_map)
    )
    df["older_left_id"] = df["older_left"].apply(
        lambda x: resolve_interval_id(x, interval_map)
    )
    df["older_right_id"] = df["older_right"].apply(
        lambda x: resolve_interval_id(x, interval_map)
    )

    df["b_interval_new"] = (
        df["older_left_id"].fillna(df["older_id"]).fillna(df["newer_id"])
    )
    df["t_interval_new"] = (
        df["older_right_id"].fillna(df["newer_id"]).fillna(df["older_id"])
    )

    # calculate whether each row actually produced an interval candidate.
    df["has_interval_candidate"] = (
        df["b_interval_new"].notna() | df["t_interval_new"].notna()
    )
    # calculate the match percentage for this candidate source column.
    candidate_row_count = len(df)
    usable_match_count = int(df["has_interval_candidate"].sum())
    match_percent = (
        100.0 * usable_match_count / candidate_row_count
        if candidate_row_count > 0
        else 0.0
    )
    console.print(
        f"[blue]Age match check:[/blue] "
        f"column={older_col} | "
        f"matches={usable_match_count}/{candidate_row_count} "
        f"({match_percent:.1f}%)"
    )
    # Only populate age when current column appears to be a valid age column.
    # Column-level gate: if >50% of candidate rows matched intervals,
    # copy the raw age text for ALL nonblank rows from this column,
    # including rows that did not individually match.
    if "age" in existing_cols and match_percent > 30.0:
        age_update_df = df[
            df["older_raw"].notna() & (df["older_raw"].astype(str).str.strip() != "")
        ][["_pkid", "older_raw"]].copy()

        if dry_run:
            console.print(
                f"[green]Dry run only; would copy raw values from[/green] "
                f"[yellow]{older_col}[/yellow] [green]into age for[/green] "
                f"{len(age_update_df)} row(s) "
                f"(match rate: {match_percent:.1f}%)"
            )
        elif not age_update_df.empty:
            values_sql = ", ".join(
                [f"(:age_pkid_{i}, :age_{i})" for i in range(len(age_update_df))]
            )

            age_params = {
                "table": target.fq_identifier,
            }
            age_update_df = age_update_df.rename(columns={"_pkid": "pkid"})
            for i, row in enumerate(age_update_df.itertuples(index=False)):
                age_params[f"age_pkid_{i}"] = int(row.pkid)
                age_params[f"age_{i}"] = str(row.older_raw).strip()

            db.run_sql(
                f"""
                UPDATE {{table}} AS tgt
                SET age = v.age_value
                FROM (
                    VALUES {values_sql}
                ) AS v(_pkid, age_value)
                WHERE tgt._pkid = v._pkid
                  AND tgt.age IS NULL
                """,
                age_params,
            )

            console.print(
                f"[green]Copied raw values from[/green] "
                f"[yellow]{older_col}[/yellow] [green]into age for[/green] "
                f"{len(age_update_df)} row(s) "
                f"(match rate: {match_percent:.1f}%)"
            )
    else:
        # leave age alone if this source column does not look age-like.
        console.print(
            f"[yellow]Skipping age copy from {older_col}:[/yellow] "
            f"match rate {match_percent:.1f}% is not > 50%"
        )

    # use the same has_interval_candidate flag for the interval update.
    update_df = df[df["has_interval_candidate"]][
        ["_pkid", "b_interval_new", "t_interval_new"]
    ].copy()

    update_df = update_df.rename(columns={"_pkid": "pkid"})

    if dry_run:
        remaining_nulls = db.run_query(
            """
            SELECT count(*)
            FROM {table}
            WHERE (b_interval IS NULL OR t_interval IS NULL)
              AND coalesce(omit, false) = false
            """,
            dict(table=target.fq_identifier),
        ).scalar()
        console.print(
            f"[green]Dry run only; no changes applied[/green] "
            f"(candidate updates: {len(update_df)})"
        )
        return remaining_nulls

    if not update_df.empty:
        values_sql = ", ".join(
            [f"(:pkid_{i}, :b_{i}, :t_{i})" for i in range(len(update_df))]
        )
        params = {"table": target.fq_identifier}

        for i, row in enumerate(update_df.itertuples(index=False)):
            params[f"pkid_{i}"] = int(row.pkid)
            params[f"b_{i}"] = (
                None if pd.isna(row.b_interval_new) else int(row.b_interval_new)
            )
            params[f"t_{i}"] = (
                None if pd.isna(row.t_interval_new) else int(row.t_interval_new)
            )

        db.run_sql(
            f"""
            UPDATE {{table}} AS tgt
            SET
                b_interval = COALESCE(tgt.b_interval, v.b_interval),
                t_interval = COALESCE(tgt.t_interval, v.t_interval)
            FROM (
                VALUES {values_sql}
            ) AS v(_pkid, b_interval, t_interval)
            WHERE tgt._pkid = v._pkid
            """,
            params,
        )

    remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE (b_interval IS NULL OR t_interval IS NULL)
          AND coalesce(omit, false) = false
        """,
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[green]Done:[/green] populated b_interval and t_interval in "
        f"{target.schema}.{target.table}. "
        f"Candidate updates: {len(update_df)}. "
        f"Remaining null age rows: {remaining_nulls}"
    )
    return remaining_nulls


normalize_cli = IngestionCLI(
    no_args_is_help=True,
    help="Normalize or bulk-fix staged table data. Selection options go before "
    "the command: normalize --slug 'arizona-%' --layer polygons copy-column ...",
)

ALL_LAYERS = ("polygons", "lines", "points")


class Layer(str, Enum):
    polygons = "polygons"
    lines = "lines"
    points = "points"


@dataclass(frozen=True)
class Selection:
    """Which maps a command runs over, from `maps.sources` and `ingest_process`."""

    slug: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    tag: tuple[str, ...] = ()
    state: tuple[str, ...] = ()
    start_after: Optional[str] = None
    layer: tuple[str, ...] = ()
    since: Optional[datetime] = None

    def layers_in(self, handled: tuple[str, ...]) -> list[str]:
        """The `--layer` tables a command should process, in its own order."""
        if not self.layer:
            return list(handled)
        unhandled = [layer for layer in self.layer if layer not in handled]
        if unhandled:
            console.print(
                f"[red]This command handles {', '.join(handled)}, "
                f"not {', '.join(unhandled)}.[/red]"
            )
            raise Exit(1)
        return [layer for layer in handled if layer in self.layer]

    def slugs(self, db) -> list[str]:
        if not self.slug and self.since is None:
            console.print(
                "[red]Pass --slug or --since before the command, e.g. "
                "normalize --slug 'arizona-%' <command>[/red]"
            )
            raise Exit(1)
        where, params = ["true"], {}
        if self.slug:
            where.append("s.slug ILIKE ANY(CAST(:slug AS text[]))")
            params.update(slug=list(self.slug))
        if self.since is not None:
            where.append("p.created_on >= CAST(:since AS timestamptz)")
            # A date without a zone is local time, not the database server's.
            params.update(since=self.since.astimezone())
        if self.exclude:
            where.append("NOT (s.slug ILIKE ANY(CAST(:exclude AS text[])))")
            params.update(exclude=list(self.exclude))
        if self.state:
            where.append("p.state = ANY(CAST(:state AS text[]))")
            params.update(state=list(self.state))
        if self.tag:
            # Every requested tag, not any of them.
            where.append(
                """
                (SELECT count(DISTINCT t.tag) FROM maps_metadata.ingest_process_tag t
                 WHERE t.source_id = s.source_id
                   AND t.tag = ANY(CAST(:tag AS text[]))) = :n_tags
                """
            )
            params.update(tag=list(self.tag), n_tags=len(set(self.tag)))
        slugs = list(
            db.run_query(
                f"""
                SELECT s.slug
                FROM maps.sources s
                JOIN maps_metadata.ingest_process p USING (source_id)
                WHERE {" AND ".join(where)}
                ORDER BY s.slug
                """,
                params,
            ).scalars()
        )
        if self.start_after is not None:
            after = next((s for s in slug_forms(self.start_after) if s in slugs), None)
            if after is None:
                console.print(
                    f"[red]--start-after {self.start_after} is not selected[/red]"
                )
                raise Exit(1)
            slugs = slugs[slugs.index(after) + 1 :]
        return slugs


@normalize_cli.callback()
def select(
    ctx: Context,
    slug: Annotated[
        Optional[list[str]],
        Option(
            "--slug", "-s", help="ILIKE pattern on the slug. Repeat for any of several."
        ),
    ] = None,
    exclude: Annotated[
        Optional[list[str]],
        Option(
            "--exclude",
            "-x",
            help="ILIKE pattern on the slug to leave out. Repeatable.",
        ),
    ] = None,
    tag: Annotated[
        Optional[list[str]],
        Option(
            "--tag",
            "-t",
            help="Ingest-process tag the map must carry. Repeat to require all.",
        ),
    ] = None,
    state: Annotated[
        Optional[list[str]],
        Option(
            "--state",
            help="Ingest-process state, e.g. ingested. Repeat for any of several.",
        ),
    ] = None,
    start_after: Annotated[
        Optional[str],
        Option(
            "--start-after",
            help="Resume: skip selected maps up to and including this slug.",
        ),
    ] = None,
    layer: Annotated[
        Optional[list[Layer]],
        Option(
            "--layer",
            "-l",
            help="The sources.{slug}_{layer} table to process. Repeatable. "
            "Default: every layer the command handles.",
        ),
    ] = None,
    since: Annotated[
        Optional[datetime],
        Option(
            "--since",
            help="Maps whose ingest process was created on or after this date "
            "(2026-11-17) or time (2026-11-17T14:00:00), local time.",
        ),
    ] = None,
):
    """Select maps by slug, ingest-process creation date, tag and state, and
    their layers."""
    ctx.obj = Selection(
        slug=tuple(slug or ()),
        exclude=tuple(exclude or ()),
        tag=tuple(tag or ()),
        state=tuple(state or ()),
        start_after=start_after,
        layer=tuple(layer.value for layer in layer or ()),
        since=since,
    )


def for_each(*handled: str):
    """Run a command once per selected map, and per layer when it names the
    layers it handles. The command's `slug` and `target` (the map's
    `sources.{slug}_{layer}` table) come from the selection, not its own options.
    A map that fails is reported and the rest still run."""

    def decorate(fn):
        signature = inspect.signature(fn)
        injected = {"slug", "target"} & set(signature.parameters)
        params = [p for p in signature.parameters.values() if p.name not in injected]

        def command(ctx: Context, **kwargs):
            selection: Selection = ctx.obj
            layers = selection.layers_in(handled) if handled else [None]
            db = get_database()
            slugs = selection.slugs(db)
            if not slugs:
                console.print("[yellow]No maps match the selection.[/yellow]")
                return

            failed: list[tuple[str, str]] = []
            for position, slug in enumerate(slugs, start=1):
                for layer in layers:
                    label = slug if layer is None else f"{slug} {layer}"
                    console.print(
                        f"\n[bold cyan]({position}/{len(slugs)}) {label}[/bold cyan]"
                    )
                    given = dict(kwargs)
                    if "slug" in injected:
                        given["slug"] = slug
                    if "target" in injected:
                        given["target"] = TableTarget(
                            schema="sources", table=staging_table(slug, layer)
                        )
                    try:
                        fn(**given)
                    except Exception as e:
                        db.session.rollback()
                        failed.append((label, f"{type(e).__name__}: {e}"))
                        console.print(f"[red]Failed[/red] [bold]{label}[/bold]: {e}")

            done = len(slugs) * len(layers) - len(failed)
            console.print(f"\n[green]Finished:[/green] {done}/{done + len(failed)}")
            for label, message in failed:
                console.print(f"  [red]{label}[/red]: {message}")
            if failed:
                raise Exit(1)

        ctx_param = inspect.Parameter(
            "ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context
        )
        command.__name__ = fn.__name__
        command.__doc__ = fn.__doc__
        command.__signature__ = signature.replace(parameters=[ctx_param, *params])
        command.__annotations__ = {"ctx": Context} | {
            p.name: p.annotation for p in params
        }
        return command

    return decorate


# _____________________________________CALCULATE AZIMUTH/DIP DIRECTION____________________________
def calculate_dip_dir_from_columns(
    target: TableTarget,
    strike_col: str,
    strike_cardinal_col: str,
    dip_col: str,
    dip_cardinal_col: str,
    dry_run: bool = False,
):
    """Populate dip_dir from strike and dip-direction information.

    Rules:
    - If strike is present, compute the two perpendicular azimuths:
      (strike + 90) % 360 and (strike - 90) % 360.
    - If dip-cardinal is present, choose the perpendicular option whose compass
      direction matches the recorded dip-cardinal.
    - Otherwise default to right-hand rule and use (strike + 90) % 360.
    - Leave dip_dir null when strike is null or blank.
    """
    db = get_database()

    strike_col = validate_identifier(strike_col, "strike column")
    strike_cardinal_col = validate_identifier(
        strike_cardinal_col, "strike cardinal column"
    )
    dip_col = validate_identifier(dip_col, "dip column")
    dip_cardinal_col = validate_identifier(dip_cardinal_col, "dip cardinal column")

    existing_cols = get_existing_columns(target)
    required = {
        strike_col,
        strike_cardinal_col,
        dip_col,
        dip_cardinal_col,
        "dip_dir",
    }
    missing = required - existing_cols
    if missing:
        raise ValueError(
            f"Missing required columns in {target.schema}.{target.table}: "
            f"{', '.join(sorted(missing))}"
        )

    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[blue]Calculating dip_dir for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"using strike=[yellow]{strike_col}[/yellow], "
        f"strike-cardinal=[yellow]{strike_cardinal_col}[/yellow], "
        f"dip=[yellow]{dip_col}[/yellow], "
        f"dip-cardinal=[yellow]{dip_cardinal_col}[/yellow] "
        f"across {row_count} rows"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return

    db.run_sql(
        """
        WITH base AS (
            SELECT
                t._pkid,
                CASE
                    WHEN t.{strike_col} IS NULL THEN NULL
                    WHEN trim(t.{strike_col}::text) = '' THEN NULL
                    ELSE ((t.{strike_col}::text)::numeric % 360 + 360) % 360
                END AS strike_azimuth,
                lower(trim(nullif(t.{dip_cardinal_col}::text, ''))) AS dip_cardinal
            FROM {table} AS t
        ),
        candidates AS (
            SELECT
                b._pkid,
                b.strike_azimuth,
                ((b.strike_azimuth + 90) % 360) AS rhs_dir,
                ((b.strike_azimuth + 270) % 360) AS lhs_dir,
                b.dip_cardinal
            FROM base AS b
            WHERE b.strike_azimuth IS NOT NULL
        ),
        resolved AS (
            SELECT
                c._pkid,
                CASE
                    WHEN c.dip_cardinal IS NULL THEN c.rhs_dir

                    WHEN c.dip_cardinal IN ('n', 'north')
                        THEN CASE
                            WHEN c.rhs_dir >= 315 OR c.rhs_dir < 45 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 315 OR c.lhs_dir < 45 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END
                    WHEN c.dip_cardinal IN ('e', 'east')
                        THEN CASE
                            WHEN c.rhs_dir >= 45 AND c.rhs_dir < 135 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 45 AND c.lhs_dir < 135 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END
                    WHEN c.dip_cardinal IN ('s', 'south')
                        THEN CASE
                            WHEN c.rhs_dir >= 135 AND c.rhs_dir < 225 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 135 AND c.lhs_dir < 225 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END
                    WHEN c.dip_cardinal IN ('w', 'west')
                        THEN CASE
                            WHEN c.rhs_dir >= 225 AND c.rhs_dir < 315 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 225 AND c.lhs_dir < 315 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END

                    WHEN c.dip_cardinal IN ('ne', 'northeast', 'north-east')
                        THEN CASE
                            WHEN c.rhs_dir >= 0 AND c.rhs_dir < 90 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 0 AND c.lhs_dir < 90 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END
                    WHEN c.dip_cardinal IN ('se', 'southeast', 'south-east')
                        THEN CASE
                            WHEN c.rhs_dir >= 90 AND c.rhs_dir < 180 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 90 AND c.lhs_dir < 180 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END
                    WHEN c.dip_cardinal IN ('sw', 'southwest', 'south-west')
                        THEN CASE
                            WHEN c.rhs_dir >= 180 AND c.rhs_dir < 270 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 180 AND c.lhs_dir < 270 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END
                    WHEN c.dip_cardinal IN ('nw', 'northwest', 'north-west')
                        THEN CASE
                            WHEN c.rhs_dir >= 270 AND c.rhs_dir < 360 THEN c.rhs_dir
                            WHEN c.lhs_dir >= 270 AND c.lhs_dir < 360 THEN c.lhs_dir
                            ELSE c.rhs_dir
                        END

                    ELSE c.rhs_dir
                END AS dip_dir_value
            FROM candidates AS c
        )
        UPDATE {table} AS t
        SET dip_dir = resolved.dip_dir_value
        FROM resolved
        WHERE t._pkid = resolved._pkid
        """,
        dict(
            table=target.fq_identifier,
            strike_col=Identifier(strike_col),
            strike_cardinal_col=Identifier(strike_cardinal_col),
            dip_col=Identifier(dip_col),
            dip_cardinal_col=Identifier(dip_cardinal_col),
        ),
    )

    console.print(
        f"[green]Done:[/green] populated dip_dir in {target.schema}.{target.table}"
    )


# `maps.points` check constraints (dip_lt_90, dip_positive, strike_lt_360,
# strike_positive) as (column, min, max). NULL never violates a CHECK
# constraint, so bounds only apply to non-null values.
#
# dip_dir has its own pair (direction_lt_360, direction_positive) but is
# deliberately left out here -- fixing it needs a compass-direction judgment
# call this command doesn't make, so it's shown for context only and never
# edited, cleared or used to flag a row.
ORIENTATION_BOUNDS = {
    "strike": (0, 360),
    "dip": (0, 90),
}


def _warn_if_still_out_of_range(col: str, value: Optional[int]):
    lo, hi = ORIENTATION_BOUNDS[col]
    if value is not None and not (lo <= value <= hi):
        console.print(
            f"  [yellow]warning:[/yellow] {col}={value} is still outside "
            f"[{lo}, {hi}] -- applying it anyway"
        )


def review_orientation_values(target: TableTarget, dry_run: bool = False):
    """Interactively walk every non-omitted point whose strike or dip would
    fail a `maps.points` check constraint, and let the user resolve it.

    For each flagged row the user can: edit strike and/or dip, clear both to
    NULL, omit the row from insertion entirely, apply a bulk fix to every row
    sharing the same offending value, or leave it for later (skip). Only rows
    that would actually be inserted are shown -- already-omitted rows are not
    this command's business. dip_dir is shown for context but is out of scope
    for this pass.
    """
    db = get_database()
    existing_cols = get_existing_columns(target)
    required = set(ORIENTATION_BOUNDS) | {"_pkid", "dip_dir"}
    missing = required - existing_cols
    if missing:
        raise ValueError(
            f"{target.schema}.{target.table} is missing column(s): "
            f"{', '.join(sorted(missing))}"
        )

    violation = " OR ".join(
        f"({col} IS NOT NULL AND ({col} < {lo} OR {col} > {hi}))"
        for col, (lo, hi) in ORIENTATION_BOUNDS.items()
    )
    rows = db.run_query(
        f"""
        SELECT _pkid, orig_id, strike, dip, dip_dir, point_type, certainty, comments
        FROM {{table}}
        WHERE NOT coalesce(omit, false) AND ({violation})
        ORDER BY _pkid
        """,
        dict(table=target.fq_identifier),
    ).fetchall()

    if not rows:
        console.print(
            f"[green]No out-of-range strike/dip rows in[/green] "
            f"{target.schema}.{target.table}"
        )
        return

    console.print(
        f"[blue]{len(rows)} row(s) with out-of-range strike/dip values in[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold]"
    )

    # Rows a bulk fix already disposed of; skipped without re-prompting.
    resolved_pkids: set[int] = set()

    for i, row in enumerate(rows, start=1):
        if row._pkid in resolved_pkids:
            continue

        console.print(
            f"\n[bold]{i}/{len(rows)}[/bold] "
            f"[dim]_pkid={row._pkid} orig_id={row.orig_id}[/dim]"
        )
        console.print(
            f"  strike=[yellow]{row.strike}[/yellow]  "
            f"dip=[yellow]{row.dip}[/yellow]  "
            f"dip_dir=[dim]{row.dip_dir}[/dim] [dim](not editable here)[/dim]"
        )
        console.print(f"  point_type={row.point_type!r}  certainty={row.certainty!r}")
        if row.comments:
            console.print(f"  comments={row.comments!r}")

        action = Prompt.ask(
            "  [edit/clear/omit/bulk/skip]",
            choices=["edit", "clear", "omit", "bulk", "skip"],
            default="skip",
            show_choices=False,
        )

        if action == "skip":
            continue

        if action == "omit":
            console.print("  [yellow]-> omitting row[/yellow]")
            if not dry_run:
                db.run_sql(
                    "UPDATE {table} SET omit = true WHERE _pkid = :pkid",
                    dict(table=target.fq_identifier, pkid=row._pkid),
                )
            continue

        if action == "clear":
            console.print("  [yellow]-> clearing strike/dip to NULL[/yellow]")
            if not dry_run:
                db.run_sql(
                    """
                    UPDATE {table}
                    SET strike = NULL, dip = NULL
                    WHERE _pkid = :pkid
                    """,
                    dict(table=target.fq_identifier, pkid=row._pkid),
                )
            continue

        if action == "bulk":
            # Same offending value shows up on many rows (e.g. a -999 sentinel
            # for "unknown"); fix every row sharing it in one shot instead of
            # walking each one individually.
            bad_cols = [
                col
                for col, (lo, hi) in ORIENTATION_BOUNDS.items()
                if getattr(row, col) is not None and not (lo <= getattr(row, col) <= hi)
            ]
            col = Prompt.ask(
                "  bulk column",
                choices=list(ORIENTATION_BOUNDS),
                default=bad_cols[0] if len(bad_cols) == 1 else None,
                show_choices=True,
            )
            current = getattr(row, col)
            match_raw = Prompt.ask(
                f"  match value (blank = this row's {col}={current})",
                default="",
                show_default=False,
            ).strip()
            try:
                match_value = current if match_raw == "" else float(match_raw)
            except ValueError:
                console.print(
                    f"  [red]'{match_raw}' is not a number, aborting bulk[/red]"
                )
                continue
            new_raw = Prompt.ask(
                f"  new {col} for every matching row ('null' to clear)"
            ).strip()
            if new_raw.lower() in ("null", "none"):
                new_value = None
            else:
                try:
                    new_value = int(round(float(new_raw)))
                except ValueError:
                    console.print(
                        f"  [red]'{new_raw}' is not a number, aborting bulk[/red]"
                    )
                    continue
            _warn_if_still_out_of_range(col, new_value)

            select_or_update = (
                f"SELECT _pkid FROM {{table}} WHERE {col} = :match AND NOT coalesce(omit, false)"
                if dry_run
                else (
                    f"UPDATE {{table}} SET {col} = :new WHERE {col} = :match "
                    f"AND NOT coalesce(omit, false) RETURNING _pkid"
                )
            )
            affected = (
                db.run_query(
                    select_or_update,
                    dict(table=target.fq_identifier, match=match_value, new=new_value),
                )
                .scalars()
                .all()
            )
            resolved_pkids.update(affected)
            verb = "would set" if dry_run else "set"
            console.print(
                f"  [yellow]-> {verb} {col}={new_value} for {len(affected)} row(s) "
                f"where {col} = {match_value}[/yellow]"
            )
            continue

        # action == "edit": prompt per field, blank keeps the current value.
        updates: dict[str, Optional[int]] = {}
        for col in ORIENTATION_BOUNDS:
            entered = Prompt.ask(
                f"  new {col} (blank to leave unchanged, 'null' to clear)",
                default="",
                show_default=False,
            ).strip()
            if entered == "":
                continue
            if entered.lower() in ("null", "none"):
                updates[col] = None
                continue
            try:
                updates[col] = int(round(float(entered)))
            except ValueError:
                console.print(
                    f"  [red]'{entered}' is not a number, skipping {col}[/red]"
                )

        if not updates:
            console.print("  [dim]No changes entered[/dim]")
            continue

        for col, value in updates.items():
            _warn_if_still_out_of_range(col, value)

        console.print(f"  [yellow]-> setting {updates}[/yellow]")
        if dry_run:
            continue

        set_clause = ", ".join(f"{col} = :{col}" for col in updates)
        params = dict(updates)
        params["table"] = target.fq_identifier
        params["pkid"] = row._pkid
        db.run_sql(f"UPDATE {{table}} SET {set_clause} WHERE _pkid = :pkid", params)

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
    else:
        console.print("[green]Done:[/green] orientation review complete")


# ____________________________________CLI COMMANDS________________________________________________


@normalize_cli.command("copy-column")
@for_each("polygons", "lines", "points")
def normalize_copy_column(
    target: TableTarget,
    src_cols: list[str] = Option(
        ...,
        "--src",
        help="Source column to copy from. Repeat --src for multiple columns.",
    ),
    dst: str = Option(..., "--dst", help="Destination column to fill"),
    no_prompt: bool = Option(
        False,
        "--no-prompt",
        help="Do not prompt interactively for more source columns; use only the provided --src values.",
    ),
):
    """
    Copy values from one or more source columns into a destination column,
    filling only currently-null destination rows.

    - processes provided source columns in order
    - stops early once all null destination rows are filled
    - skips invalid source columns and continues
    - optionally falls back to interactive prompting unless --no-prompt is used
    """
    db = get_database()
    dst = dst.strip()
    cleaned_srcs = [col.strip() for col in src_cols if col.strip() != ""]

    if dst == "":
        raise ValueError("Destination column --dst cannot be empty")

    existing_cols = get_existing_columns(target)
    if dst not in existing_cols:
        raise ValueError(
            f"Destination column '{dst}' does not exist in {target.schema}.{target.table}"
        )
    remaining_nulls: Optional[int] = None
    for src in cleaned_srcs:
        try:
            remaining_nulls = copy_column_values(
                target=target,
                src=src,
                dst=dst,
            )
        except ValueError as e:
            console.print(
                f"[yellow]Skipping source column[/yellow] "
                f"[bold]{src}[/bold] -> [bold]{dst}[/bold]: {e}"
            )
            continue

        if remaining_nulls == 0:
            console.print(f"[green]All null {dst} rows have been filled[/green]")
            return

        console.print(
            f"[yellow]{remaining_nulls} rows still have null {dst} values.[/yellow]"
        )
    if not no_prompt:
        next_src = Prompt.ask(
            f"Map values from another column into [bold]{dst}[/bold]? "
            "Enter a column name or press Enter to exit",
            default="",
            show_default=False,
        ).strip()

        while next_src != "":
            try:
                remaining_nulls = copy_column_values(
                    target=target,
                    src=next_src,
                    dst=dst,
                )
            except ValueError as e:
                console.print(
                    f"[yellow]Skipping source column[/yellow] "
                    f"[bold]{next_src}[/bold] -> [bold]{dst}[/bold]: {e}"
                )
                next_src = Prompt.ask(
                    f"Map values from another column into [bold]{dst}[/bold]? "
                    "Enter a column name or press Enter to exit",
                    default="",
                    show_default=False,
                ).strip()
                continue

            if remaining_nulls == 0:
                console.print(f"[green]All null {dst} rows have been filled[/green]")
                return

            console.print(
                f"[yellow]{remaining_nulls} rows still have null {dst} values.[/yellow]"
            )
            next_src = Prompt.ask(
                f"Map values from another column into [bold]{dst}[/bold]? "
                "Enter a column name or press Enter to exit",
                default="",
                show_default=False,
            ).strip()
    if remaining_nulls is None:
        remaining_nulls = db.run_query(
            """
            SELECT count(*)
            FROM {table}
            WHERE {dst} IS NULL
              AND coalesce(omit, false) = false
            """,
            dict(
                table=target.fq_identifier,
                dst=Identifier(dst),
            ),
        ).scalar()
    console.print("[green]Finished copy-column[/green]")


@normalize_cli.command("copy-preferred-fields")
@for_each("polygons", "lines", "points")
def normalize_copy_preferred_columns(
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively map source columns into the preferred destination columns for
    points, lines, or polygons tables. Press Enter to skip a destination field.
    """
    copy_preferred_column_values_interactive(
        target=target,
        dry_run=dry_run,
    )


@normalize_cli.command("add-preferred-columns")
@for_each("polygons", "lines", "points")
def normalize_add_preferred_columns(
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Add any missing preferred standard columns for a points, lines, or polygons
    staging table. Existing columns are skipped.
    """
    add_preferred_columns(target=target, dry_run=dry_run)


@normalize_cli.command("add-metadata")
@for_each()
def normalize_add_metadata(
    slug: str,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively update metadata fields in maps.sources for each selected map.
    """
    add_metadata_interactive(slug, dry_run=dry_run)


@normalize_cli.command("add-metadata-csv")
def normalize_add_metadata_csv(
    csv_path: Path = Argument(..., help="Path to metadata CSV file"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Update maps.sources metadata from a CSV file.

    - matches rows by slug
    - skips blank/null CSV values
    - updates only the fields present and non-empty for each row
    """
    process_metadata_csv(csv_path=csv_path, dry_run=dry_run)


@normalize_cli.command("calculate-age")
@for_each("polygons")
def normalize_calculate_age(
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Ask, but write nothing"),
):
    """
    Review the polygons with no b_interval or t_interval, one map unit at a
    time: shows its name, descrip, age and intervals, asks for its age ("Late
    Pleistocene", "Miocene to Pliocene", or interval ids) and sets b_interval
    and t_interval from the answer, and age to it. Select maps before the command:
    normalize --slug 'arizona-%' --since 2026-11-17 calculate-age
    """
    review_ages(get_database(), target, dry_run=dry_run)


@normalize_cli.command("copy-age")
@for_each("polygons")
def normalize_copy_ages(
    target: TableTarget,
    slug: str,
    older_cols: list[str] = Option(
        ...,
        "--older",
        help="Column containing older age. Repeat --older/--newer for multiple pairs.",
    ),
    newer_cols: list[str] = Option(
        ...,
        "--newer",
        help="Column containing younger age. Repeat --older/--newer for multiple pairs.",
    ),
    no_prompt: bool = Option(
        False,
        "--no-prompt",
        help="Do not prompt interactively for more columns; use only the provided pairs.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Copy older/newer age columns into b_interval and t_interval.

    - processes provided older/newer pairs in order
    - stops early once all null age rows are filled
    - optionally falls back to interactive prompting unless --no-prompt is used
    - tracks columns that do not reduce remaining null age rows
    - appends 'some ages null;' to maps_metadata.ingest_process.comments if nulls remain
      after all provided/prompted pairs are exhausted
    """
    db = get_database()
    cleaned_older = [col.strip() for col in older_cols if col.strip() != ""]
    cleaned_newer = [col.strip() for col in newer_cols if col.strip() != ""]

    if len(cleaned_older) != len(cleaned_newer):
        raise ValueError(
            "The number of --older values must match the number of --newer values."
        )

    prev_remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE (b_interval IS NULL OR t_interval IS NULL)
          AND coalesce(omit, false) = false
        """,
        dict(table=target.fq_identifier),
    ).scalar()

    remaining_nulls: Optional[int] = None

    last_no_match_col: Optional[str] = None
    detected_non_age_col: Optional[str] = None

    for older_col, newer_col in zip(cleaned_older, cleaned_newer):
        try:
            remaining_nulls = copy_age_columns(
                target=target,
                older_col=older_col,
                newer_col=newer_col,
                dry_run=dry_run,
            )
        except ValueError as e:
            console.print(
                f"[yellow]Skipping pair[/yellow] "
                f"[bold]{older_col}[/bold] / [bold]{newer_col}[/bold]: {e}"
            )
            continue

        if remaining_nulls == prev_remaining_nulls:
            # this column found no new age matches
            last_no_match_col = older_col
        elif remaining_nulls < prev_remaining_nulls:
            # this column found matches
            if last_no_match_col is not None and detected_non_age_col is None:
                detected_non_age_col = last_no_match_col

        prev_remaining_nulls = remaining_nulls

        if remaining_nulls == 0:
            console.print("[green]All null age rows have been filled[/green]")
            break

    console.print(
        f"[yellow]{remaining_nulls} rows still have null age values.[/yellow]"
    )

    if not no_prompt and (remaining_nulls is None or remaining_nulls > 0):
        next_older = Prompt.ask(
            "Map values from another column into [bold]b_interval[/bold]? "
            "Enter an older-age column name or press Enter to exit",
            default="",
            show_default=False,
        ).strip()

        while next_older != "":
            next_newer = Prompt.ask(
                "Map values from another column into [bold]t_interval[/bold]? "
                "Enter a younger-age column name or press Enter to exit",
                default="",
                show_default=False,
            ).strip()

            if next_newer == "":
                break

            try:
                remaining_nulls = copy_age_columns(
                    target=target,
                    older_col=next_older,
                    newer_col=next_newer,
                    dry_run=dry_run,
                )
            except ValueError as e:
                console.print(
                    f"[yellow]Skipping pair[/yellow] "
                    f"[bold]{next_older}[/bold] / [bold]{next_newer}[/bold]: {e}"
                )
                next_older = Prompt.ask(
                    "Map values from another column into [bold]b_interval[/bold]? "
                    "Enter an older-age column name or press Enter to exit",
                    default="",
                    show_default=False,
                ).strip()
                continue

            if remaining_nulls == prev_remaining_nulls:
                last_no_match_col = next_older
            elif remaining_nulls < prev_remaining_nulls:
                if last_no_match_col is not None and detected_non_age_col is None:
                    detected_non_age_col = last_no_match_col

            prev_remaining_nulls = remaining_nulls

            if remaining_nulls == 0:
                console.print("[green]All null age rows have been filled[/green]")
                break

            console.print(
                f"[yellow]{remaining_nulls} rows still have null age values.[/yellow]"
            )

            next_older = Prompt.ask(
                "Map values from another column into [bold]b_interval[/bold]? "
                "Enter an older-age column name or press Enter to exit",
                default="",
                show_default=False,
            ).strip()

    if remaining_nulls is None:
        remaining_nulls = db.run_query(
            """
            SELECT count(*)
            FROM {table}
            WHERE (b_interval IS NULL OR t_interval IS NULL)
              AND coalesce(omit, false) = false
            """,
            dict(table=target.fq_identifier),
        ).scalar()
    if remaining_nulls > 0:
        append_ingest_comment(slug, comment="some ages null;", dry_run=dry_run)
        add_ingest_process_tag(slug=slug, tag=AGES_NULL_TAG, dry_run=dry_run)
    else:
        remove_ingest_process_tag(slug=slug, tag=AGES_NULL_TAG, dry_run=dry_run)

    console.print("[green]Finished copy-age[/green]")

    if detected_non_age_col is not None:
        print(detected_non_age_col)


@normalize_cli.command("copy-orig-id")
@for_each("polygons", "lines", "points")
def normalize_copy_orig_id(
    target: TableTarget,
    src_cols: list[str] = Option(
        ...,
        "--src",
        help="One or more source columns to try for orig_id. The first valid column is copied.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Try one or more source columns for orig_id.

    A source column is valid only if, across all non-omitted rows, its values are
    non-null, nonblank, integer-castable, and unique.

    The first valid source column is copied into orig_id.
    """
    candidates = list(
        dict.fromkeys(validate_identifier(src, "source column") for src in src_cols)
    )
    copy_orig_id_from_candidates(
        target=target,
        candidates=candidates,
        dry_run=dry_run,
    )


@normalize_cli.command("calculate-orig-id")
@for_each("polygons", "lines", "points")
def normalize_calculate_orig_id(
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Give every polygon, line and point an orig_id, layer by layer: the map's
    own id where an id-named column (objectid, *_id, *-id, *#) holds a unique
    integer per feature, otherwise 1, 2, 3, ... An orig_id that is already
    unique is kept. Select maps before the command:
    normalize --slug 'arizona-%' --since 2026-11-17 calculate-orig-id
    """
    calculate_orig_id(get_database(), target, dry_run=dry_run)


@normalize_cli.command("copy-line-type")
@for_each("lines")
def normalize_copy_line_type(
    target: TableTarget,
    src: str = Option(..., "--src", help="Initial source column to map from"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Map a source column into the linework type column using values from maps.lines.
    If nulls remain in type after a pass, the user is prompted to map another column.
    Press Enter to stop.
    """
    table = target.table
    if not table.endswith("_lines"):
        raise ValueError("copy-line-type is intended for _lines tables")
    next_col = src.strip()
    while next_col != "":
        remaining_nulls = copy_line_type_from_column(
            target=target,
            src_col=next_col,
            dry_run=dry_run,
        )
        if remaining_nulls == 0:
            console.print("[green]All null type rows have been filled[/green]")
            break

        console.print(
            f"[yellow]{remaining_nulls} rows still have null type values.[/yellow]"
        )
        next_col = Prompt.ask(
            "Map values from another column into [bold]type[/bold]? "
            "Enter a column name or press Enter to exit",
            default="",
            show_default=False,
        ).strip()
    if next_col == "":
        console.print("[green]Finished copy-line-type[/green]")


@normalize_cli.command("copy-point-type")
@for_each("points")
def normalize_copy_point_type(
    target: TableTarget,
    src: str = Option(..., "--src", help="Initial source column to map from"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Map a source column into the point_type column using values from maps.points.
    If nulls remain in point_type after a pass, the user is prompted to map another column.
    Press Enter to stop.
    """
    table = target.table
    if not table.endswith("_points"):
        raise ValueError("copy-point-type is intended for _points tables")
    next_col = src.strip()
    while next_col != "":
        remaining_nulls = copy_point_type_from_column(
            target=target,
            src_col=next_col,
            dry_run=dry_run,
        )
        if remaining_nulls == 0:
            console.print("[green]All null point_type rows have been filled[/green]")
            break
        console.print(
            f"[yellow]{remaining_nulls} rows still have null point_type values.[/yellow]"
        )
        next_col = Prompt.ask(
            "Map values from another column into [bold]point_type[/bold]? "
            "Enter a column name or press Enter to exit",
            default="",
            show_default=False,
        ).strip()
    if next_col == "":
        console.print("[green]Finished copy-point-type[/green]")


@normalize_cli.command("null-column")
@for_each("polygons", "lines", "points")
def normalize_null_column(
    target: TableTarget,
    column: str = Argument(..., help="Column to set to NULL"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Set all values in a specified column to NULL.
    """
    null_column_values(target=target, column=column, dry_run=dry_run)


@normalize_cli.command("null-value")
@for_each("polygons", "lines", "points")
def normalize_null_value(
    target: TableTarget,
    column: str = Option(..., "--column", help="Column to check"),
    value: str = Option(..., "--value", help="String value to replace with NULL"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Set a cell to NULL when the specified column exactly matches a given string.
    """
    null_matching_value(
        target=target,
        column=column,
        value=value,
        dry_run=dry_run,
    )


@normalize_cli.command("calculate-strat-name")
@for_each("polygons")
def normalize_calculate_strat_name(
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Fill strat_name from each polygon's name, or its descrip where name gives
    no strat name, exactly as ingest does (map_strat_name_ingest): names in Macrostrat's
    lexicon first, then a best guess from a name's form (Belmont Granite).

    Rows that already have a strat_name are left alone; run
    `null-column strat_name` first to recompute every row.
    """
    from .ingest import _blank, map_strat_name_ingest

    db = get_database()
    existing = get_existing_columns(target)
    if "strat_name" not in existing:
        raise ValueError("No strat_name column; run add-preferred-columns first")
    columns = [c for c in ("_pkid", "name", "descrip", "strat_name") if c in existing]
    rows = db.run_query(
        f"SELECT {', '.join(columns)} FROM {{table}}",
        dict(table=target.fq_identifier),
    ).all()
    df = pd.DataFrame(rows, columns=columns)
    before = df["strat_name"].copy()
    df = map_strat_name_ingest(db, df)
    filled = df[_blank(before) & ~_blank(df["strat_name"])]

    console.print(
        f"[green]{len(filled)}[/green] of {len(df)} rows get a strat_name; "
        f"{int(_blank(df['strat_name']).sum())} stay null"
    )
    text = filled["name"] if "name" in filled else filled["descrip"]
    for source, strat_name in list(zip(text, filled["strat_name"]))[:10]:
        console.print(f"  {str(source)[:60]} [dim]->[/dim] {strat_name}")
    if dry_run or filled.empty:
        if dry_run:
            console.print("[green]Dry run only; no changes applied[/green]")
        return

    db.run_query(
        """
        UPDATE {table} t SET strat_name = v.strat_name
        FROM unnest(CAST(:ids AS bigint[]), CAST(:names AS text[]))
            AS v(_pkid, strat_name)
        WHERE t._pkid = v._pkid
        """,
        dict(
            table=target.fq_identifier,
            ids=[int(i) for i in filled["_pkid"]],
            names=list(filled["strat_name"]),
        ),
    )
    db.session.commit()
    console.print("[green]Finished calculate-strat-name[/green]")


@normalize_cli.command("strat-name-report")
def normalize_strat_name_report(
    ctx: Context,
    out: Optional[Path] = Option(
        None,
        "--out",
        help="Markdown note to append the report to, e.g. one in the workbench's "
        "Investigations folder. Created if it does not exist.",
    ),
):
    """
    Count, for each selected map's polygons, the strat_name values Macrostrat's
    lexicon has (macrostrat.lookup_strat_names, by strat_name or rank_name) and
    those it does not. After ingest or calculate-strat-name, the first are the
    lexicon matches and the second the best guesses from a name's form, such as
    Belmont Granite. Writes nothing to the database.
    """
    from datetime import date

    selection: Selection = ctx.obj
    selection.layers_in(("polygons",))
    db = get_database()
    slugs = selection.slugs(db)
    if not slugs:
        console.print("[yellow]No maps match the selection.[/yellow]")
        return

    lexicon = set()
    for row in db.run_query(
        "SELECT strat_name, rank_name FROM macrostrat.lookup_strat_names"
    ):
        lexicon.update(n.strip().lower() for n in (row.strat_name, row.rank_name) if n)

    rows = []
    for slug in slugs:
        target = TableTarget(schema="sources", table=staging_table(slug, "polygons"))
        try:
            columns = get_existing_columns(target)
        except ValueError:
            rows.append(dict(slug=slug, note="no polygons table"))
            continue
        if "strat_name" not in columns:
            rows.append(dict(slug=slug, note="no strat_name column"))
            continue
        values = (
            db.run_query(
                "SELECT strat_name FROM {table}", dict(table=target.fq_identifier)
            )
            .scalars()
            .all()
        )
        row = dict(slug=slug, polygons=len(values), named=0, lexicon=0, guess=0)
        row.update(mixed=0, lexicon_names=set(), guess_names=set(), note="")
        for value in values:
            names = [n.strip() for n in str(value or "").split(";") if n.strip()]
            if not names:
                continue
            row["named"] += 1
            known = [n.lower() in lexicon for n in names]
            for name, is_known in zip(names, known):
                row["lexicon_names" if is_known else "guess_names"].add(name)
            row[
                "lexicon" if all(known) else "guess" if not any(known) else "mixed"
            ] += 1
        rows.append(row)

    counted = [r for r in rows if not r["note"]]
    keys = ("polygons", "named", "lexicon", "guess", "mixed")
    totals = {k: sum(r[k] for r in counted) for k in keys}
    header = (
        "| Map | Polygons | With strat_name | Lexicon | Best guess | Both "
        "| Lexicon names | Best-guess names |"
    )
    lines = [header, "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in rows:
        if r["note"]:
            lines.append(f"| {r['slug']} | {r['note']} | | | | | | |")
            continue
        lines.append(
            f"| {r['slug']} | {r['polygons']} | {r['named']} | {r['lexicon']} "
            f"| {r['guess']} | {r['mixed']} | {len(r['lexicon_names'])} "
            f"| {len(r['guess_names'])} |"
        )
    lines.append(
        f"| **Total ({len(counted)} maps)** | {totals['polygons']} | {totals['named']} "
        f"| {totals['lexicon']} | {totals['guess']} | {totals['mixed']} | | |"
    )

    guesses = [r for r in counted if r["guess_names"]]
    for line in lines:
        console.print(line, markup=False, highlight=False)
    for r in guesses:
        console.print(
            f"[dim]{r['slug']} best guesses:[/dim] {', '.join(sorted(r['guess_names']))}"
        )
    if out is None:
        return

    chosen = [
        f"--{flag.replace('_', '-')} {value}"
        for flag, values in vars(selection).items()
        for value in (
            values if isinstance(values, tuple) else [values] if values else []
        )
    ]
    section = [
        f"## [[{date.today().isoformat()}]] - strat_name sources, {len(counted)} maps",
        "",
        f"`macrostrat maps staging normalize {' '.join(chosen)} strat-name-report`.",
        "Polygons count once each: *Lexicon* when every name in their strat_name is "
        "in `macrostrat.lookup_strat_names`, *Best guess* when none is, *Both* "
        "otherwise.",
        "",
        *lines,
        "",
    ]
    if guesses:
        section += ["Best-guess names:", ""]
        section += [
            f"- **{r['slug']}**: {', '.join(sorted(r['guess_names']))}" for r in guesses
        ]
        section.append("")
    out = Path(out)
    existing = (
        out.read_text() if out.exists() else '---\nrepos:\n  - "[[macrostrat]]"\n---\n'
    )
    out.write_text(existing.rstrip("\n") + "\n\n" + "\n".join(section))
    console.print(f"[green]Appended to[/green] {out}")


@normalize_cli.command("replace-value")
@for_each("polygons", "lines", "points")
def normalize_replace_value(
    target: TableTarget,
    column: str = Option(..., "--col", help="Column to update"),
    old_value: str = Option(..., "--old", help="Value to replace"),
    new_value: str = Option(..., "--new", help="Replacement value"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Replace a specific value in a column with a new value.
    """
    replace_column_value(
        target=target,
        column=column,
        old_value=old_value,
        new_value=new_value,
        dry_run=dry_run,
    )


@normalize_cli.command("replace-value-with-column")
@for_each("polygons", "lines", "points")
def normalize_replace_value_with_column(
    target: TableTarget,
    src: str = Option(..., "--src", help="Source column to copy values from"),
    dst: str = Option(..., "--dst", help="Destination column to update"),
    dst_val: str = Option(
        ...,
        "--dst-val",
        help="Value in dst to replace with the row-wise src value",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Replace a specific value in dst with the value from src in the same row.
    """
    replace_value_with_column(
        target=target,
        src=src,
        dst=dst,
        dst_val=dst_val,
        dry_run=dry_run,
    )


@normalize_cli.command("remove-word-in-string")
@for_each("polygons", "lines", "points")
def normalize_remove_word_in_string(
    target: TableTarget,
    src: str = Option(..., "--src", help="Column to clean in place"),
    word: str = Option(..., "--word", help="String fragment to remove"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Remove all occurrences of a word/string fragment from a column.
    """
    remove_word_in_string(
        target=target,
        src=src,
        word=word,
        dry_run=dry_run,
    )


@normalize_cli.command("merge-column")
@for_each("polygons", "lines", "points")
def normalize_merge_column(
    target: TableTarget,
    col_one: str = Option(..., "--dst", help="Destination column"),
    col_two: str = Option(..., "--src", help="Column to merge into dst column"),
    separator: str = Option(..., "--separator", help="Separator between values"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Merge values from col-two into col-one using a user-provided separator.
    """
    merge_column_values(
        target=target,
        col_one=col_one,
        col_two=col_two,
        separator=separator,
        dry_run=dry_run,
    )


@normalize_cli.command("calculate-dip-dir")
@for_each("points")
def normalize_calculate_dip_dir(
    target: TableTarget,
    strike_col: str = Option(..., "--str", help="Numeric strike column"),
    strike_cardinal_col: str = Option(
        ..., "--str-cardinal", help="Cardinal strike column"
    ),
    dip_col: str = Option(..., "--dip", help="Numeric dip column"),
    dip_cardinal_col: str = Option(
        ..., "--dip-cardinal", help="Cardinal dip-direction column"
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Calculate dip_dir from strike and dip-direction information.
    Defaults to right-hand rule when dip-cardinal is missing.
    """
    calculate_dip_dir_from_columns(
        target=target,
        strike_col=strike_col,
        strike_cardinal_col=strike_cardinal_col,
        dip_col=dip_col,
        dip_cardinal_col=dip_cardinal_col,
        dry_run=dry_run,
    )


@normalize_cli.command("points-review-orientation")
@for_each("points")
def normalize_points_review_orientation(
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively resolve strike/dip values that would violate a
    `maps.points` check constraint (e.g. strike=555, dip=410), across the
    `_points` table of every selected map.

        macrostrat maps staging normalize --slug 'arizona-%' \\
            --exclude 'arizona-adgm-%' points-review-orientation

    dip_dir is shown for context but is out of scope for this pass -- it needs
    a compass-direction judgment call this command doesn't make.

    For each flagged row you can:
    - edit: enter new value(s) for strike and/or dip
    - clear: set strike and dip to NULL
    - omit: set omit=true so the row is not inserted at all
    - skip: leave the row unchanged for now
    """
    review_orientation_values(target=target, dry_run=dry_run)


@normalize_cli.command("update-state")
@for_each()
def normalize_update_status(
    slug: str,
    state: str = Option(..., "--state", help="New ingest state"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Update maps_metadata.ingest_process.state for each selected map.
    """
    update_ingest_status(slug, state=state, dry_run=dry_run)


@normalize_cli.command("fuzzy-match-lith")
@for_each("polygons")
def normalize_fuzzy_match_lith(
    target: TableTarget,
    src: Optional[str] = Option(
        None,
        "--src",
        help="Source column to read instead of name and descrip.",
    ),
    threshold: float = Option(
        0.85,
        "--threshold",
        help="Per-token fuzzy-match threshold between 0 and 1.",
    ),
    limit: Optional[int] = Option(
        None,
        "--limit",
        help="Optional limit on number of rows to inspect.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Compute per-row fuzzy match percentages for a lithology text column against
    macrostrat.liths and macrostrat.lith_atts vocabularies.

    - if --src is provided, use that column
    - otherwise read name and descrip together, whichever the table has
    - with neither, the last non-empty legend...e column
    - every row with a match gets the matched liths and atts in lith
    """

    if src is not None and src.strip() != "":
        src_col = validate_identifier(src, "source column")
        existing_cols = get_existing_columns(target)
        if src_col not in existing_cols:
            raise ValueError(
                f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
            )
    else:
        existing_cols = get_existing_columns(target)
        src_col = [c for c in ("name", "descrip") if c in existing_cols]
        if not src_col:
            src_col = find_last_nonempty_column_ending_with_e(target)

    calculate_lith_fuzzy_match_percentages(
        target=target,
        src_col=src_col,
        threshold=threshold,
        limit=limit,
        dry_run=dry_run,
    )


@normalize_cli.command("match-remaining-cols")
@for_each("polygons", "lines")
def match_remaining_cols(
    target: TableTarget,
    non_age_col: str = Argument(
        ...,
        help="Column identified as not an age column.",
    ),
    preview_limit: int = Option(
        30,
        "--preview-limit",
        help="Number of distinct preview values to print for each candidate column.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively merge legend columns into name, starting from non_age_col and
    continuing through columns_between to second_last_col.

    After the initial pass, optionally allow skipped ('n') columns to be merged
    into another user-specified destination column.
    """
    db = get_database()
    existing_cols = get_existing_columns(target)

    non_age_col, columns_between, second_last_col = (
        get_columns_between_non_age_and_second_last(
            target=target,
            non_age_col=non_age_col,
        )
    )

    merge_cols = [non_age_col] + columns_between + [second_last_col]

    # de-duplicate while preserving order
    deduped_cols: list[str] = []
    seen = set()
    for col in merge_cols:
        col = validate_identifier(col, "selected column")
        if col not in seen:
            seen.add(col)
            deduped_cols.append(col)

    console.print(f"[green]non_age_col:[/green] [bold]{non_age_col}[/bold]")
    console.print(
        f"[green]columns_between:[/green] "
        f"{', '.join(columns_between) if columns_between else '(none)'}"
    )
    console.print(f"[green]second_last_col:[/green] [bold]{second_last_col}[/bold]")

    remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE (name IS NULL OR trim(name::text) = '')
          AND coalesce(omit, false) = false
        """,
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[green]Initial remaining null name rows:[/green] [bold]{remaining_nulls}[/bold]"
    )

    no_cols: list[str] = []

    for col in deduped_cols:
        preview_values = get_distinct_preview_values_for_column(
            target=target,
            column=col,
            limit=preview_limit,
        )

        console.print("")
        console.print(f"[bold cyan]Column:[/bold cyan] {col}")

        if preview_values:
            console.print("[dim]Preview values:[/dim]")
            for value in preview_values:
                console.print(f"  - {value}")
        else:
            console.print("[dim]Preview values: (none)[/dim]")

        response = (
            Prompt.ask(
                "Would you like to merge into 'name'? [y/n, Enter to exit]",
                default="",
                show_default=False,
            )
            .strip()
            .lower()
        )

        if response == "":
            console.print("[yellow]Exiting match-remaining-cols[/yellow]")
            return

        if response == "n":
            no_cols.append(col)
            console.print(f"[yellow]Skipping[/yellow] column [bold]{col}[/bold]")
            continue

        if response != "y":
            console.print(
                "[yellow]Invalid response. Please enter 'y', 'n', or press Enter to exit.[/yellow]"
            )
            return

        remaining_nulls = merge_column_into_destination(
            target=target,
            src_col=col,
            dst_col="name",
            dry_run=dry_run,
        )

        console.print(
            f"[green]Remaining null name rows:[/green] [bold]{remaining_nulls}[/bold]"
        )

        if remaining_nulls == 0:
            console.print("[green]All null name rows have been filled[/green]")

    if not no_cols:
        console.print("[green]Finished match-remaining-cols[/green]")
        return

    console.print("")
    console.print("[bold cyan]Skipped columns:[/bold cyan]")
    for col in no_cols:
        preview_values = get_distinct_preview_values_for_column(
            target=target,
            column=col,
            limit=preview_limit,
        )
        console.print(f"[bold]{col}[/bold]")
        if preview_values:
            for value in preview_values:
                console.print(f"  - {value}")
        else:
            console.print("  - (none)")

    response = (
        Prompt.ask(
            "Would you like to merge the no columns elsewhere? [y/n]",
            default="n",
            show_default=False,
        )
        .strip()
        .lower()
    )

    if response != "y":
        console.print("[green]Finished match-remaining-cols[/green]")
        return

    for curr_no_col in no_cols:
        preview_values = get_distinct_preview_values_for_column(
            target=target,
            column=curr_no_col,
            limit=preview_limit,
        )

        console.print("")
        console.print(f"[bold cyan]No column:[/bold cyan] {curr_no_col}")
        if preview_values:
            console.print("[dim]Preview values:[/dim]")
            for value in preview_values:
                console.print(f"  - {value}")
        else:
            console.print("[dim]Preview values: (none)[/dim]")

        while True:
            dst_col = Prompt.ask(
                f"What column do you want to merge {curr_no_col} into? "
                f"(press Enter to skip)",
                default="",
                show_default=False,
            ).strip()

            if dst_col == "":
                console.print(
                    f"[yellow]Skipping[/yellow] no column [bold]{curr_no_col}[/bold]"
                )
                break

            if dst_col not in existing_cols:
                console.print(
                    f"[red]Wrong column name entered:[/red] [bold]{dst_col}[/bold]"
                )
                continue

            remaining_dst_nulls = merge_column_into_destination(
                target=target,
                src_col=curr_no_col,
                dst_col=dst_col,
                dry_run=dry_run,
            )

            console.print(
                f"[green]Remaining null {dst_col} rows:[/green] "
                f"[bold]{remaining_dst_nulls}[/bold]"
            )
            break

    console.print("[green]Finished match-remaining-cols[/green]")


@normalize_cli.command("update-process-tag")
@for_each(*ALL_LAYERS)
def normalize_update_process_flag(
    slug: str,
    target: TableTarget,
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Tag each selected map '<layer> processed' (polygons processed, lines
    processed, points processed) for each selected layer.
    """
    add_ingest_process_tag(slug, f"{target.layer} processed", dry_run=dry_run)


@normalize_cli.command("add-tag")
@for_each()
def normalize_add_tag(
    slug: str,
    tag: str = Argument(..., help="Tag text, e.g. 'some ages null'"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Add a maps_metadata.ingest_process_tag row with an explicit tag.

    Unlike update-process-tag, the text is given rather than inferred from the
    layer. Adding a tag the map already has is a no-op.
    """
    add_ingest_process_tag(slug, tag, dry_run=dry_run)


#: The tag for a map whose staged features of a kind come from more than one
#: source layer, set at ingest (data-integration's Arizona `ingest`).
EXTRA_LAYERS_TAGS = {
    "polygons": "extra-poly-layers",
    "lines": "extra-line-layers",
    "points": "extra-point-layers",
}


def omit_source_layers(
    db, slug: str, target: TableTarget, patterns: list[str], dry_run: bool = False
) -> None:
    """Set omit = true on a table's features whose source_layer matches one of
    `patterns` (ILIKE), then drop the map's extra-*-layers tag for the table's
    kind if one source layer or none is left not omitted."""
    columns = get_existing_columns(target)
    if not {"source_layer", "omit"} <= columns:
        console.print("[dim]No table with source_layer and omit[/dim]")
        return
    params = dict(table=target.fq_identifier, patterns=list(patterns))
    matched = db.run_query(
        """
        SELECT source_layer, count(*) FILTER (WHERE omit IS NOT TRUE) AS n
        FROM {table}
        WHERE source_layer ILIKE ANY(CAST(:patterns AS text[]))
        GROUP BY 1 ORDER BY 1
        """,
        params,
    ).all()
    if not matched:
        console.print("[dim]No matching source layer[/dim]")
        return
    for layer, n in matched:
        console.print(
            f"  omit {n:>7,}  {layer}"
            if n
            else f"  [dim]already omitted  {layer}[/dim]"
        )
    if not dry_run and any(n for _, n in matched):
        db.run_query(
            """
            UPDATE {table} SET omit = true
            WHERE source_layer ILIKE ANY(CAST(:patterns AS text[]))
              AND omit IS NOT TRUE
            """,
            params,
        )
        db.session.commit()

    kept = db.run_query(
        """
        SELECT coalesce(array_agg(DISTINCT source_layer ORDER BY source_layer), '{{}}')
        FROM {table}
        WHERE omit IS NOT TRUE
          AND NOT source_layer ILIKE ANY(CAST(:patterns AS text[]))
        """,
        params,
    ).scalar()
    tag = EXTRA_LAYERS_TAGS[target.layer]
    if len(kept) > 1:
        console.print(f"  [yellow]{tag} kept:[/yellow] still {', '.join(kept)}")
    elif _has_ingest_process_tag(db, slug, tag):
        remove_ingest_process_tag(slug, tag, dry_run=dry_run)
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")


@normalize_cli.command("omit-source-layer")
@for_each(*ALL_LAYERS)
def normalize_omit_source_layer(
    slug: str,
    target: TableTarget,
    patterns: list[str] = Option(
        ...,
        "--source-layer",
        help="source_layer to omit, an ILIKE pattern ('%DataSourcePolys%'). "
        "Repeatable.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Set omit = true on the features of a source layer, such as the
    DataSourcePolys staged beside MapUnitPolys. Then removes the map's
    extra-poly-layers (extra-line-layers, extra-point-layers) tag if one source
    layer is left. Never clears an omit.
    """
    omit_source_layers(get_database(), slug, target, patterns, dry_run=dry_run)


@normalize_cli.command("remove-tag")
@for_each()
def normalize_remove_tag(
    slug: str,
    tag: str = Argument(..., help="Tag text to remove"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Remove a maps_metadata.ingest_process_tag row. Silent if the tag is absent.
    """
    remove_ingest_process_tag(slug, tag, dry_run=dry_run)
