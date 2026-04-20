import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher
import pandas as pd
from psycopg2.sql import SQL, Identifier
from rich.console import Console
from rich.prompt import Prompt
from typer import Argument, Option

from macrostrat.map_integration.commands.prepare_fields.utils import (
    LineworkTableUpdater,
    PointsTableUpdater,
    PolygonTableUpdater,
)
from macrostrat.map_integration.database import get_database
from macrostrat.map_integration.utils import IngestionCLI

console = Console()

"""
Future subcommands to add
fill-null
rename-values
trim-whitespace
lowercase-column
coalesce-columns
"""

CONTEXT_FILE = Path("macrostrat_staging_context.json")
DEFAULT_MAP_CONTEXT = {
    "schema": "sources",
    "slug": None,
    "table": None,
}
STRAT_NAME_SUFFIXES = [
    "formation",
    "fm",
    "group",
    "gp",
    "member",
    "mbr",
]

PRE_INTERVAL_MAP = {
    "jurassic": "triassic",
}


def load_map_context() -> dict:
    """Load persisted map context from disk."""
    if not CONTEXT_FILE.exists():
        return DEFAULT_MAP_CONTEXT.copy()

    try:
        data = json.loads(CONTEXT_FILE.read_text())
    except Exception:
        return DEFAULT_MAP_CONTEXT.copy()

    return {
        "schema": data.get("schema", "sources"),
        "slug": data.get("slug"),
        "table": data.get("table"),
    }


def save_map_context(context: dict):
    """Persist map context to disk."""
    CONTEXT_FILE.write_text(json.dumps(context, indent=2))


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


MY_MAP = {
    "schema": "sources",
    "slug": None,
    "table": None,
}


def get_current_target() -> TableTarget:
    """Return the current table target from persisted context."""
    context = load_map_context()
    schema = context.get("schema")
    table = context.get("table")

    if not schema or not table:
        raise ValueError(
            "No current map/layer is set. Run 'set-map' and then 'set-layer' first."
        )

    return TableTarget(schema=schema, table=table)



def strip_strat_name_suffixes(value: str) -> str:
    """Strip common stratigraphic rank suffixes from the end of a value."""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text == "":
        return text

    suffix_pattern = r"(?:\s+|,)+(formation|fm|group|gp|member|mbr)\.?\s*$"
    while True:
        updated = re.sub(suffix_pattern, "", text, flags=re.IGNORECASE).strip(" ,;:-")
        if updated == text:
            break
        text = updated

    return text

def set_current_map(slug: str):
    """Set the current map slug and default base table."""
    slug = validate_identifier(slug, "slug")
    context = load_map_context()
    context["schema"] = "sources"
    context["slug"] = slug
    context["table"] = slug
    save_map_context(context)


def set_current_layer(layer: str):
    """Set the current layer table from the stored slug."""
    layer = layer.strip().lower()
    if layer not in {"points", "lines", "polygons"}:
        raise ValueError("layer must be one of: points, lines, polygons")

    context = load_map_context()
    slug = context.get("slug")
    if not slug:
        raise ValueError("No slug is set. Run 'set-map <slug>' first.")

    context["table"] = f"{slug}_{layer}"
    save_map_context(context)


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

def append_ingest_comment_for_current_slug(
    comment: str,
    dry_run: bool = False,
):
    """Append a comment fragment to maps_metadata.ingest_process.comments for the
    current CONTEXT_FILE slug, avoiding duplicate appends.
    """
    db = get_database()
    slug = (load_map_context().get("slug") or "").strip()
    comment = comment.strip()
    if slug == "":
        raise ValueError(
            "No slug is set in context. Run 'set-map <slug>' first."
        )
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
        WHERE slug = :slug
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
        columns_between = e_cols[second_last_idx + 1:non_age_idx]
    else:
        columns_between = e_cols[non_age_idx + 1:second_last_idx]

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


def find_second_last_nonempty_column_ending_with_e(target: TableTarget) -> str:
    """Return the second-last column by ordinal position whose name ends with 'e'
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
    matches: list[str] = []
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
            matches.append(col)
        if len(matches) == 2:
            return matches[1]
    raise ValueError(
        f"Could not find a second non-empty column ending with 'e' in "
        f"{target.schema}.{target.table}"
    )

def tokenize_lith_text(value: str) -> list[str]:
    text = re.sub(r"[^A-Za-z0-9]+", " ", str(value)).strip().lower()
    if text == "":
        return []
    return [tok for tok in text.split() if tok]


def get_lith_reference_terms() -> set[str]:
    """Build a normalized vocabulary from macrostrat.liths and macrostrat.lith_atts."""
    db = get_database()
    rows = db.run_query(
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

        UNION

        SELECT lith_att::text AS term
        FROM macrostrat.lith_atts
        WHERE lith_att IS NOT NULL
        """
    ).fetchall()

    out = set()
    for row in rows:
        term = re.sub(r"\s+", " ", str(row.term)).strip().lower()
        if term != "":
            out.add(term)
    return out



def best_fuzzy_match(token: str, reference_terms: set[str]) -> tuple[Optional[str], float]:
    """Return the best matching reference term and its similarity ratio."""
    token = token.strip().lower()
    if token == "":
        return None, 0.0

    best_term = None
    best_ratio = 0.0

    for ref in reference_terms:
        ratio = SequenceMatcher(None, token, ref).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_term = ref
            if best_ratio == 1.0:
                break

    return best_term, best_ratio


def calculate_lith_fuzzy_match_percentages(
    target: TableTarget,
    src_col: str,
    threshold: float = 0.85,
    row_copy_threshold_percent: float = 10.0,
    limit: Optional[int] = None,
    dry_run: bool = False,
):
    """Print per-row fuzzy match percentages for tokens in src_col against
    macrostrat lith/lith_att vocabularies.

    If a row's fuzzy match percentage is greater than row_copy_threshold_percent,
    write the matched canonical lith strings directly into the lith column for
    that same row/_pkid.
    """
    db = get_database()
    src_col = validate_identifier(src_col, "source column")
    existing_cols = get_existing_columns(target)

    if src_col not in existing_cols:
        raise ValueError(
            f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
        )
    if "lith" not in existing_cols:
        raise ValueError(
            f"Destination column 'lith' does not exist in {target.schema}.{target.table}"
        )

    reference_terms = get_lith_reference_terms()

    limit_sql = ""
    params = {
        "table": target.fq_identifier,
        "src_col": Identifier(src_col),
    }
    if limit is not None:
        limit_sql = "LIMIT :limit"
        params["limit"] = limit

    rows = db.run_query(
        f"""
        SELECT _pkid, {{src_col}} AS src_value
        FROM {{table}}
        WHERE {{src_col}} IS NOT NULL
          AND trim({{src_col}}::text) <> ''
          AND coalesce(omit, false) = false
        ORDER BY _pkid
        {limit_sql}
        """,
        params,
    ).fetchall()

    console.print(
        f"[blue]Evaluating lith fuzzy matches for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"using [yellow]{src_col}[/yellow] across {len(rows)} row(s)"
    )

    total_rows = 0
    total_word_count = 0
    total_match_percent = 0.0
    updates: list[tuple[int, str]] = []

    for row in rows:
        tokens = tokenize_lith_text(row.src_value)
        word_count = len(tokens)
        total_rows += 1
        total_word_count += word_count

        if not tokens:
            percent = 0.0
            total_match_percent += percent
            console.print(
                f"_pkid={row._pkid} | words=0 | match=0.0% | matched= | value={row.src_value}"
            )
            continue

        matched_count = 0
        matched_terms: list[str] = []
        seen_terms = set()

        for token in tokens:
            best_term, score = best_fuzzy_match(token, reference_terms)
            if best_term is not None and score >= threshold:
                matched_count += 1
                if best_term not in seen_terms:
                    seen_terms.add(best_term)
                    matched_terms.append(best_term)

        percent = 100.0 * matched_count / word_count
        total_match_percent += percent
        matched_string = ", ".join(matched_terms)

        console.print(
            f"_pkid={row._pkid} | words={word_count} | match={percent:.1f}% | "
            f"matched={matched_string} | value={row.src_value}"
        )

        if percent > row_copy_threshold_percent and matched_string != "":
            updates.append((row._pkid, matched_string))

    if updates and not dry_run:
        values_sql = ", ".join(
            [f"(:pkid_{i}, :lith_{i})" for i in range(len(updates))]
        )
        update_params = {
            "table": target.fq_identifier,
            "lith_col": Identifier("lith"),
        }

        for i, (pkid, lith_string) in enumerate(updates):
            update_params[f"pkid_{i}"] = pkid
            update_params[f"lith_{i}"] = lith_string

        db.run_sql(
            f"""
            UPDATE {{table}} AS t
            SET {{lith_col}} = v.lith_string
            FROM (
                VALUES {values_sql}
            ) AS v(_pkid, lith_string)
            WHERE t._pkid = v._pkid
            """,
            update_params,
        )

        console.print(
            f"[green]Done:[/green] wrote matched lith strings into "
            f"[bold]lith[/bold] for {len(updates)} row(s) with match > "
            f"{row_copy_threshold_percent:.1f}%"
        )

    elif dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")

    avg_words = (total_word_count / total_rows) if total_rows > 0 else 0.0
    avg_match_percent = (total_match_percent / total_rows) if total_rows > 0 else 0.0

    console.print(
        f"[green]Summary:[/green] "
        f"column={src_col} | rows={total_rows} | "
        f"avg_words={avg_words:.2f} | avg_match={avg_match_percent:.1f}%"
    )



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
            f"[blue]Adding[/blue] [bold]{col_name}[/bold] " f"[dim]({col_type})[/dim]"
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
    - If col_one is null/blank, set col_one = col_two
    - Otherwise set col_one = col_one || separator || col_two
    """
    db = get_database()
    col_one = validate_identifier(col_one, "first column")
    col_two = validate_identifier(col_two, "second column")
    existing_cols = get_existing_columns(target)

    if col_one not in existing_cols:
        console.print(f"[yellow]Skipping merge. Column '{col_one}' does not exist in {target.schema}.{target.table}[/yellow]")
        return
    if col_two not in existing_cols:
        console.print(f"[yellow]Skipping merge. Column '{col_two}' does not exist in {target.schema}.{target.table}[/yellow]")
        return
    row_count = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE {col_two} IS NOT NULL
          AND trim({col_two}::text) <> ''
          AND lower(trim({col_two}::text)) <> 'unknown'
          AND lower(trim({col_two}::text)) <> 'none'
        """,
        dict(
            table=target.fq_identifier,
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
            f"Could not merge column '{col_two}' into '{col_one}'. "
            f"Original error: {e}"
        ) from e

    console.print(
        f"[green]Done:[/green] merged values from {col_two} into {col_one} "
        f"in {target.schema}.{target.table}"
    )


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
    dry_run: bool = False,
) -> int:
    """Copies values from column `src` into currently-null rows of column `dst`
    in the target table. Validates that both columns exist before executing.
    Returns the count of remaining null destination rows.
    """
    db = get_database()
    src = validate_identifier(src, "src column")
    dst = validate_identifier(dst, "dst column")
    existing_cols = get_existing_columns(target)

    if src not in existing_cols:
        raise ValueError(
            f"Source column '{src}' does not exist in {target.schema}.{target.table}"
        )
    if dst not in existing_cols:
        raise ValueError(
            f"Destination column '{dst}' does not exist in {target.schema}.{target.table}"
        )

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

    if dry_run:
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
        console.print("[green]Dry run only; no changes applied[/green]")
        return remaining_nulls

    db.run_sql(
        """
        UPDATE {table}
        SET {dst} = {src}
        WHERE {dst} IS NULL
          AND {src} IS NOT NULL
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


def update_ingest_status(
    state: str,
    dry_run: bool = False,
):
    """Update maps_metadata.ingest_process.state for a given slug.
    If slug is not provided, use the current MY_MAP slug.
    """
    db = get_database()
    state = state.strip()
    slug = load_map_context().get("slug").strip()

    if slug == "":
        raise ValueError(
            "slug cannot be empty. Run 'set-map <slug>' first or pass --slug."
        )
    if state == "":
        raise ValueError("state cannot be empty")

    match_count = db.run_query(
        """
        SELECT count(*)
        FROM maps_metadata.ingest_process
        WHERE slug = :slug
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
        WHERE slug = :slug
        """,
        dict(slug=slug, state=state),
    )

    db.run_sql(
        """
    UPDATE maps_metadata.ingest_process
    SET comments = 'metadata manually processed; polygons processed; lines processed; points processed;'
    WHERE slug = :slug
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


def get_source_row_for_table(table_name: str):
    """Looks up the maps.sources row whose primary_table matches the given table name. Raises a ValueError if no
    matching row is found. Returns the full database row including source_id and slug.
    """
    db = get_database()
    row = db.run_query(
        """
        SELECT source_id, primary_table, slug
        FROM maps.sources
        WHERE primary_table = :table_name
        """,
        dict(table_name=table_name),
    ).fetchone()
    if row is None:
        raise ValueError(
            f"Could not find a row in maps.sources with primary_table = '{table_name}'"
        )
    return row


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


def add_metadata_interactive(
    table_name: str,
    dry_run: bool = False,
):
    """Interactively prompts the user to enter values for each metadata field in METADATA_FIELDS, then applies
    them as an UPDATE to the matching maps.sources row. When dry_run is True, the prepared updates are printed
    but not written to the database."""
    db = get_database()
    source_row = get_source_row_for_table(table_name)
    console.print(
        f"[blue]Editing metadata for[/blue] "
        f"[bold]maps.sources[/bold] row with "
        f"[yellow]primary_table = {table_name}[/yellow]"
    )
    console.print(
        f"[dim]Matched source_id={source_row.source_id}, slug={source_row.slug}[/dim]"
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
def calculate_age_intervals(
    target: TableTarget,
    col_one: str,
    col_two: str,
    dry_run: bool = False,
):
    """Populates b_interval and t_interval on the target table by matching values from two user-supplied
    text columns against macrostrat.intervals, with a fallback to the era column. Both destination columns are
    set to the same resolved interval ID. Raises a ValueError if required columns are missing.
    """
    db = get_database()
    col_one = validate_identifier(col_one, "first age column")
    col_two = validate_identifier(col_two, "second age column")
    existing_cols = get_existing_columns(target)
    if col_one not in existing_cols:
        raise ValueError(
            f"Column '{col_one}' does not exist in {target.schema}.{target.table}"
        )
    if col_two not in existing_cols:
        raise ValueError(
            f"Column '{col_two}' does not exist in {target.schema}.{target.table}"
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
        f"[blue]Calculating ages for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"using [yellow]{col_one}[/yellow], then [yellow]{col_two}[/yellow], "
        f"then fallback [yellow]era[/yellow] across {row_count} rows"
    )
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return
    sql = """
        WITH interval_lookup AS (
            SELECT lower(trim(interval_name)) AS interval_name, min(id) AS id
            FROM macrostrat.intervals
            GROUP BY 1
        )
        UPDATE {table} AS t
        SET
            b_interval = COALESCE(
                (SELECT il.id
                 FROM interval_lookup il
                 WHERE il.interval_name = lower(trim(nullif({col_one}::text, '')))),
                (SELECT il.id
                 FROM interval_lookup il
                 WHERE il.interval_name = lower(trim(nullif({col_two}::text, '')))),
                (SELECT il.id
                 FROM interval_lookup il
                 WHERE il.interval_name = lower(trim(nullif(era::text, ''))))
            ),
            t_interval = COALESCE(
                (SELECT il.id
                 FROM interval_lookup il
                 WHERE il.interval_name = lower(trim(nullif({col_one}::text, '')))),
                (SELECT il.id
                 FROM interval_lookup il
                 WHERE il.interval_name = lower(trim(nullif({col_two}::text, '')))),
                (SELECT il.id
                 FROM interval_lookup il
                 WHERE il.interval_name = lower(trim(nullif(era::text, ''))))
            )
    """
    db.run_sql(
        sql,
        dict(
            table=target.fq_identifier,
            col_one=Identifier(col_one),
            col_two=Identifier(col_two),
        ),
    )
    console.print(
        f"[green]Done:[/green] populated b_interval and t_interval in "
        f"{target.schema}.{target.table}"
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
        "SELECT count(*) FROM {table}",
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
    if value is None:
        return None

    text = str(value).strip()
    if text == "":
        return None

    text = re.sub(r"\(\?\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\([^)]*ma[^)]*\)\s*$", "", text, flags=re.IGNORECASE)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text).strip().lower()

    return text or None


def parse_age_range(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = normalize_age_text(value)
    if text is None:
        return None, None

    if text == "jurassic and pre-jurassic":
        return "jurassic", "triassic"

    if " to " in text:
        left, right = text.split(" to ", 1)
        return left.strip(), right.strip()

    if " and " in text:
        left, right = text.split(" and ", 1)
        right = right.strip()
        if right.startswith("pre-"):
            right_base = right.replace("pre-", "", 1).strip()
            return left.strip(), PRE_INTERVAL_MAP.get(right_base, right_base)
        return left.strip(), right

    if "-" in text:
        left, right = text.split("-", 1)
        return left.strip(), right.strip()

    return text, text


def copy_orig_id_from_column(
    target: TableTarget,
    src_col: str,
    dry_run: bool = False,
):
    """Copy src_col into orig_id only if every row is non-null/nonblank and all
    values are unique across the table.
    """
    db = get_database()
    src_col = validate_identifier(src_col, "source column")
    existing_cols = get_existing_columns(target)

    if src_col not in existing_cols:
        raise ValueError(
            f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
        )
    if "orig_id" not in existing_cols:
        raise ValueError(
            f"Destination column 'orig_id' does not exist in {target.schema}.{target.table}"
        )

    stats = db.run_query(
        """
        SELECT
            count(*) AS total_rows,
            count({src_col}) AS nonnull_rows,
            count(DISTINCT {src_col}) AS distinct_rows,
            count(*) FILTER (
                WHERE {src_col} IS NOT NULL
                  AND trim({src_col}::text) <> ''
            ) AS nonblank_rows
        FROM {table}
        WHERE coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src_col=Identifier(src_col),
        ),
    ).fetchone()

    total_rows = stats.total_rows
    nonnull_rows = stats.nonnull_rows
    distinct_rows = stats.distinct_rows
    nonblank_rows = stats.nonblank_rows

    if (
        total_rows == 0
        or nonnull_rows != total_rows
        or nonblank_rows != total_rows
        or distinct_rows != total_rows
    ):
        console.print(
            f"[yellow]invalid {src_col} column and not copied into orig_id[/yellow]"
        )
        return

    console.print(
        f"[blue]Copying[/blue] [yellow]{src_col}[/yellow] -> [yellow]orig_id[/yellow] "
        f"across {total_rows} rows"
    )

    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return

    db.run_sql(
        """
        UPDATE {table}
        SET orig_id = {src_col}
        WHERE coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src_col=Identifier(src_col),
        ),
    )

    console.print(
        f"[green]Done:[/green] copied values from {src_col} to orig_id "
        f"in {target.schema}.{target.table}"
    )


def copy_age_columns(
    target: TableTarget,
    older_col: str,
    newer_col: str,
    dry_run: bool = False,
) -> int:
    """Copy age text from source columns into b_interval and t_interval using
    pandas for normalization/parsing and one final bulk SQL update.
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

    df["older_norm"] = df["older_raw"].apply(normalize_age_text)
    df["newer_norm"] = df["newer_raw"].apply(normalize_age_text)

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
    df["older_id"] = df["older_norm"].map(interval_map)
    df["newer_id"] = df["newer_norm"].map(interval_map)
    df["older_left_id"] = df["older_left"].map(interval_map)
    df["older_right_id"] = df["older_right"].map(interval_map)

    # Bulk-copy raw older_col into age only if this column has at least 3
    # usable interval matches after normalization/parsing.
    if "age" in existing_cols:
        usable_match_count = (
            df["older_id"].notna()
            | df["older_left_id"].notna()
            | df["older_right_id"].notna()
            | df["newer_id"].notna()
        ).sum()

        if usable_match_count >= 3:
            if dry_run:
                console.print(
                    f"[green]Dry run only; would copy raw values from[/green] "
                    f"[yellow]{older_col}[/yellow] [green]into age[/green] "
                    f"(usable normalized interval matches: {int(usable_match_count)})"
                )
            else:
                db.run_sql(
                    """
                    UPDATE {table}
                    SET age = {older_col}
                    WHERE age IS NULL
                      AND {older_col} IS NOT NULL
                      AND trim({older_col}::text) <> ''
                    """,
                    dict(
                        table=target.fq_identifier,
                        older_col=Identifier(older_col),
                    ),
                )
                console.print(
                    f"[green]Copied raw values from[/green] "
                    f"[yellow]{older_col}[/yellow] [green]into age[/green] "
                    f"(usable normalized interval matches: {int(usable_match_count)})"
                )

    df["b_interval_new"] = (
        df["older_left_id"]
        .fillna(df["older_id"])
        .fillna(df["newer_id"])
    )
    df["t_interval_new"] = (
        df["older_right_id"]
        .fillna(df["newer_id"])
        .fillna(df["older_id"])
    )


    update_df = df[
        df["b_interval_new"].notna() | df["t_interval_new"].notna()
    ][["_pkid", "b_interval_new", "t_interval_new"]].copy()

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
    help="Normalize or bulk-fix staged table data.",
)


# ___________________________________MAP STRAT_NAMES______________________________________________
def extract_capitalized_phrase_candidates(value: str) -> list[str]:
    s = str(value).strip()
    if s == "":
        return []

    candidates: list[str] = []
    seen = set()

    def add_candidate(text: str, allow_single_word: bool = False):
        text = re.sub(r"\s+", " ", text).strip(" ,;:-")
        if not text:
            return
        if not allow_single_word and len(text.split()) < 2:
            return
        key = text.lower()
        if key not in seen:
            seen.add(key)
            candidates.append(text)

    # keep full original phrase, even if one word
    add_candidate(s, allow_single_word=True)

    simplified = re.sub(r"\([^)]*\)", "", s)
    simplified = re.sub(r"\s*-\s*\d+\s*$", "", simplified).strip()
    add_candidate(simplified, allow_single_word=True)

    m = re.search(r"\bof\s+(.+)$", simplified, flags=re.IGNORECASE)
    if m:
        tail = m.group(1).strip()
        add_candidate(tail)
        tail_tokens = tail.split()
        if len(tail_tokens) >= 2:
            add_candidate(" ".join(tail_tokens[:2]))
    tokens = simplified.split()
    capitalized = [t for t in tokens if re.match(r"^[A-Z][A-Za-z0-9'.-]*$", t)]
    if len(capitalized) >= 2:
        add_candidate(" ".join(capitalized))
        add_candidate(" ".join(capitalized[:2]))
    return candidates


def find_lookup_strat_name(value: str) -> Optional[str]:
    """Resolve a source string to a canonical stratigraphic name from
    macrostrat.lookup_strat_names using progressive fallback candidates.
    Returns the matched strat_name, or None if no match is found.
    """
    db = get_database()
    normalized_value = strip_strat_name_suffixes(value)
    candidates = extract_capitalized_phrase_candidates(normalized_value)

    for candidate in candidates:
        row = db.run_query(
            """
            SELECT strat_name
            FROM macrostrat.lookup_strat_names
            WHERE strat_name ILIKE :pattern
               OR rank_name ILIKE :pattern
            ORDER BY
                CASE
                    WHEN strat_name ILIKE :exact THEN 0
                    WHEN rank_name ILIKE :exact THEN 1
                    ELSE 2
                END,
                length(coalesce(rank_name, strat_name)),
                strat_name_id
            LIMIT 1
            """,
            dict(
                pattern=f"%{candidate}%",
                exact=candidate,
            ),
        ).fetchone()

        if row is not None and row.strat_name is not None:
            return row.strat_name

    return None


def calculate_strat_name_from_column(
    target: TableTarget,
    src_col: str,
    dry_run: bool = False,
) -> int:
    """Populate strat_name from a source text column by progressively matching
    candidate substrings against macrostrat.lookup_strat_names.strat_name and
    rank_name after stripping common suffixes like Formation/Fm/Group/Gp/Member/Mbr.
    Only fills rows where strat_name is null. Leaves unmatched rows null.
    Returns the count of remaining null strat_name rows.
    """
    db = get_database()
    src_col = validate_identifier(src_col, "source column")
    existing_cols = get_existing_columns(target)

    if src_col not in existing_cols:
        raise ValueError(
            f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
        )
    if "strat_name" not in existing_cols:
        raise ValueError(
            f"Destination column 'strat_name' does not exist in {target.schema}.{target.table}"
        )

    rows = db.run_query(
        """
        SELECT _pkid, {src_col} AS src_value
        FROM {table}
        WHERE strat_name IS NULL
          AND {src_col} IS NOT NULL
          AND trim({src_col}::text) <> ''
          AND coalesce(omit, false) = false
        """,
        dict(
            table=target.fq_identifier,
            src_col=Identifier(src_col),
        ),
    ).fetchall()

    console.print(
        f"[blue]Calculating strat_name for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"from [yellow]{src_col}[/yellow] across {len(rows)} candidate rows"
    )

    if dry_run:
        remaining_nulls = db.run_query(
            """
            SELECT count(*)
            FROM {table}
            WHERE strat_name IS NULL
              AND coalesce(omit, false) = false
            """,
            dict(table=target.fq_identifier),
        ).scalar()
        console.print("[green]Dry run only; no changes applied[/green]")
        return remaining_nulls

    mappings: list[tuple[int, str]] = []
    for row in rows:
        src_value = re.sub(r"\s+", " ", str(row.src_value)).strip()
        if src_value == "":
            continue

        resolved = find_lookup_strat_name(src_value)
        if resolved is not None:
            mappings.append((row._pkid, resolved))

    if mappings:
        values_sql = ", ".join(
            [f"(:pkid_{i}, :strat_name_{i})" for i in range(len(mappings))]
        )
        params = {"table": target.fq_identifier}
        for i, (pkid, strat_name) in enumerate(mappings):
            params[f"pkid_{i}"] = pkid
            params[f"strat_name_{i}"] = strat_name

        db.run_sql(
            f"""
            UPDATE {{table}} AS t
            SET strat_name = v.strat_name
            FROM (
                VALUES {values_sql}
            ) AS v(_pkid, strat_name)
            WHERE t._pkid = v._pkid
              AND t.strat_name IS NULL
            """,
            params,
        )

    remaining_nulls = db.run_query(
        """
        SELECT count(*)
        FROM {table}
        WHERE strat_name IS NULL
          AND coalesce(omit, false) = false
        """,
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[green]Done:[/green] populated strat_name from {src_col}. "
        f"Updated rows: {len(mappings)}. "
        f"Remaining null strat_name rows: {remaining_nulls}"
    )
    return remaining_nulls

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
        f"[green]Done:[/green] populated dip_dir in " f"{target.schema}.{target.table}"
    )


# ____________________________________CLI COMMANDS________________________________________________

@normalize_cli.command("copy-column")
def normalize_copy_column(
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
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Copy values from one or more source columns into a destination column,
    filling only currently-null destination rows.

    - processes provided source columns in order
    - stops early once all null destination rows are filled
    - skips invalid source columns and continues
    - optionally falls back to interactive prompting unless --no-prompt is used
    """
    target = get_current_target()
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
                dry_run=dry_run,
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
                    dry_run=dry_run,
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
def normalize_copy_preferred_columns(
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively map source columns into the preferred destination columns for
    points, lines, or polygons tables. Press Enter to skip a destination field.
    """
    target = get_current_target()
    copy_preferred_column_values_interactive(
        target=target,
        dry_run=dry_run,
    )


@normalize_cli.command("add-preferred-columns")
def normalize_add_preferred_columns(
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Add any missing preferred standard columns for a points, lines, or polygons
    staging table. Existing columns are skipped.
    """
    target = get_current_target()
    add_preferred_columns(target=target, dry_run=dry_run)


@normalize_cli.command("add-metadata")
def normalize_add_metadata(
    table: str = Argument(..., help="Primary table name in maps.sources"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively update metadata fields in maps.sources for the row whose
    primary_table matches the provided table name.
    """
    add_metadata_interactive(table_name=table, dry_run=dry_run)


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
def normalize_calculate_age(
    col_one: str = Option(..., "--col-one", help="Primary age source column"),
    col_two: str = Option(..., "--col-two", help="Secondary age source column"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Populate b_interval and t_interval using two user-provided columns,
    falling back to era when present.
    """
    target = get_current_target()
    calculate_age_intervals(
        target=target,
        col_one=col_one,
        col_two=col_two,
        dry_run=dry_run,
    )


@normalize_cli.command("copy-age")
def normalize_copy_ages(
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
    target = get_current_target()
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
    #TODO set a maps_metadata.ingest_process_tag that indicates some ages null
    if remaining_nulls > 0:
        append_ingest_comment_for_current_slug(
            comment="some ages null;",
            dry_run=dry_run,
        )

    console.print("[green]Finished copy-age[/green]")

    if detected_non_age_col is not None:
        print(detected_non_age_col)



@normalize_cli.command("copy-orig-id")
def normalize_copy_orig_id(
    src_cols: list[str] = Option(
        ...,
        "--src",
        help="One or more source columns to try for orig_id. The first valid column is copied.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Try one or more source columns for orig_id.

    A source column is valid only if:
    - all values are non-null
    - all values are nonblank
    - all values are unique
    - distinct count equals row count

    The first valid source column is copied into orig_id.
    """
    target = get_current_target()

    cleaned_srcs: list[str] = []
    seen = set()
    for src in src_cols:
        src = validate_identifier(src, "source column")
        if src not in seen:
            seen.add(src)
            cleaned_srcs.append(src)

    for src in cleaned_srcs:
        db = get_database()
        existing_cols = get_existing_columns(target)

        if src not in existing_cols:
            console.print(
                f"[yellow]invalid {src} column and not copied into orig_id[/yellow]"
            )
            continue

        if "orig_id" not in existing_cols:
            raise ValueError(
                f"Destination column 'orig_id' does not exist in {target.schema}.{target.table}"
            )

        stats = db.run_query(
            """
            SELECT
                count(*) AS total_rows,
                count({src_col}) AS nonnull_rows,
                count(DISTINCT {src_col}) AS distinct_rows,
                count(*) FILTER (
                    WHERE {src_col} IS NOT NULL
                      AND trim({src_col}::text) <> ''
                ) AS nonblank_rows
            FROM {table}
            WHERE coalesce(omit, false) = false
            """,
            dict(
                table=target.fq_identifier,
                src_col=Identifier(src),
            ),
        ).fetchone()

        total_rows = stats.total_rows
        nonnull_rows = stats.nonnull_rows
        distinct_rows = stats.distinct_rows
        nonblank_rows = stats.nonblank_rows

        if (
            total_rows == 0
            or nonnull_rows != total_rows
            or nonblank_rows != total_rows
            or distinct_rows != total_rows
        ):
            console.print(
                f"[yellow]invalid {src} column and not copied into orig_id[/yellow]"
            )
            continue

        copy_orig_id_from_column(
            target=target,
            src_col=src,
            dry_run=dry_run,
        )
        return

    console.print("[yellow]No valid source columns found for orig_id[/yellow]")


@normalize_cli.command("copy-line-type")
def normalize_copy_line_type(
    src: str = Option(..., "--src", help="Initial source column to map from"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Map a source column into the linework type column using values from maps.lines.
    If nulls remain in type after a pass, the user is prompted to map another column.
    Press Enter to stop.
    """
    target = get_current_target()
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
def normalize_copy_point_type(
    src: str = Option(..., "--src", help="Initial source column to map from"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Map a source column into the point_type column using values from maps.points.
    If nulls remain in point_type after a pass, the user is prompted to map another column.
    Press Enter to stop.
    """
    target = get_current_target()
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
def normalize_null_column(
    column: str = Argument(..., help="Column to set to NULL"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Set all values in a specified column to NULL.
    """
    target = get_current_target()
    null_column_values(target=target, column=column, dry_run=dry_run)


@normalize_cli.command("null-value")
def normalize_null_value(
    column: str = Option(..., "--column", help="Column to check"),
    value: str = Option(..., "--value", help="String value to replace with NULL"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Set a cell to NULL when the specified column exactly matches a given string.
    """
    target = get_current_target()
    null_matching_value(
        target=target,
        column=column,
        value=value,
        dry_run=dry_run,
    )


@normalize_cli.command("calculate-strat-name")
def normalize_calculate_strat_name(
    src_cols: list[str] = Option(
        ...,
        "--src",
        help="Source column to map from. Repeat --src for multiple columns.",
    ),
    no_prompt: bool = Option(
        False,
        "--no-prompt",
        help="Do not prompt interactively for more source columns; use only the provided --src values.",
    ),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Populate strat_name from one or more source text columns by matching
    progressively smaller substrings against macrostrat.lookup_strat_names.
    Common suffixes like Formation/Fm/Group/Gp/Member/Mbr are stripped before matching.
    Unmatched rows are left as NULL.
    """
    target = get_current_target()
    db = get_database()
    cleaned_srcs = [col.strip() for col in src_cols if col.strip() != ""]
    remaining_nulls: Optional[int] = None

    for src in cleaned_srcs:
        try:
            remaining_nulls = calculate_strat_name_from_column(
                target=target,
                src_col=src,
                dry_run=dry_run,
            )
        except ValueError as e:
            console.print(
                f"[yellow]Skipping source column[/yellow] "
                f"[bold]{src}[/bold]: {e}"
            )
            continue

        if remaining_nulls == 0:
            console.print("[green]All null strat_name rows have been filled[/green]")
            return

        console.print(
            f"[yellow]{remaining_nulls} rows still have null strat_name values.[/yellow]"
        )

    if not no_prompt:
        next_src = Prompt.ask(
            "Map values from another column into [bold]strat_name[/bold]? "
            "Enter a column name or press Enter to exit",
            default="",
            show_default=False,
        ).strip()

        while next_src != "":
            try:
                remaining_nulls = calculate_strat_name_from_column(
                    target=target,
                    src_col=next_src,
                    dry_run=dry_run,
                )
            except ValueError as e:
                console.print(
                    f"[yellow]Skipping source column[/yellow] "
                    f"[bold]{next_src}[/bold]: {e}"
                )
                next_src = Prompt.ask(
                    "Map values from another column into [bold]strat_name[/bold]? "
                    "Enter a column name or press Enter to exit",
                    default="",
                    show_default=False,
                ).strip()
                continue

            if remaining_nulls == 0:
                console.print("[green]All null strat_name rows have been filled[/green]")
                return

            console.print(
                f"[yellow]{remaining_nulls} rows still have null strat_name values.[/yellow]"
            )

            next_src = Prompt.ask(
                "Map values from another column into [bold]strat_name[/bold]? "
                "Enter a column name or press Enter to exit",
                default="",
                show_default=False,
            ).strip()

    if remaining_nulls is None:
        remaining_nulls = db.run_query(
            """
            SELECT count(*)
            FROM {table}
            WHERE strat_name IS NULL
              AND coalesce(omit, false) = false
            """,
            dict(table=target.fq_identifier),
        ).scalar()

    console.print("[green]Finished calculate-strat-name[/green]")


@normalize_cli.command("replace-value")
def normalize_replace_value(
    column: str = Option(..., "--col", help="Column to update"),
    old_value: str = Option(..., "--old", help="Value to replace"),
    new_value: str = Option(..., "--new", help="Replacement value"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Replace a specific value in a column with a new value.
    """
    target = get_current_target()
    replace_column_value(
        target=target,
        column=column,
        old_value=old_value,
        new_value=new_value,
        dry_run=dry_run,
    )


@normalize_cli.command("merge-column")
def normalize_merge_column(
    col_one: str = Option(..., "--dst", help="Destination column"),
    col_two: str = Option(..., "--src", help="Column to merge into dst column"),
    separator: str = Option(..., "--separator", help="Separator between values"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Merge values from col-two into col-one using a user-provided separator.
    """
    target = get_current_target()
    merge_column_values(
        target=target,
        col_one=col_one,
        col_two=col_two,
        separator=separator,
        dry_run=dry_run,
    )


@normalize_cli.command("calculate-dip-dir")
def normalize_calculate_dip_dir(
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
    target = get_current_target()
    calculate_dip_dir_from_columns(
        target=target,
        strike_col=strike_col,
        strike_cardinal_col=strike_cardinal_col,
        dip_col=dip_col,
        dip_cardinal_col=dip_cardinal_col,
        dry_run=dry_run,
    )


@normalize_cli.command("set-map")
def normalize_set_map(
    slug: str = Argument(..., help="Map slug, e.g. california_cosorange"),
):
    set_current_map(slug)
    context = load_map_context()
    console.print(
        f"[green]Set current map:[/green] "
        f"schema={context['schema']}, slug={context['slug']}, table={context['table']}"
    )


@normalize_cli.command("set-layer")
def normalize_set_layer(
    layer: str = Argument(..., help="Layer: points, lines, or polygons"),
):
    set_current_layer(layer)
    context = load_map_context()
    console.print(
        f"[green]Set current layer:[/green] "
        f"schema={context['schema']}, table={context['table']}"
    )


@normalize_cli.command("get-map")
def normalize_show_map():
    """
    Show the current persisted map context.
    """
    console.print(f"[blue]Current MY_MAP:[/blue] {load_map_context()}")


@normalize_cli.command("update-status")
def normalize_update_status(
    state: str = Option(..., "--state", help="New ingest state"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Update maps_metadata.ingest_process.state for the current map slug
    or an explicitly provided slug.
    """
    update_ingest_status(
        state=state,
        dry_run=dry_run,
    )

@normalize_cli.command("fuzzy-match-lith")
def normalize_fuzzy_match_lith(
    src: Optional[str] = Option(
        None,
        "--src",
        help="Optional source column to use instead of auto-detecting the last non-empty column ending with 'e'.",
    ),
    threshold: float = Option(
        0.85,
        "--threshold",
        help="Per-token fuzzy-match threshold between 0 and 1.",
    ),
    row_copy_threshold_percent: float = Option(
        10.0,
        "--row-copy-threshold",
        help="If a row's match percentage is greater than this value, copy matched lith strings directly into lith.",
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
    - otherwise auto-detect the last non-empty column whose name ends with 'e'
    - if a row's match percentage is > --row-copy-threshold, write the matched
      lith strings directly into lith for that same row/_pkid
    """
    target = get_current_target()

    if src is not None and src.strip() != "":
        src_col = validate_identifier(src, "source column")
        existing_cols = get_existing_columns(target)
        if src_col not in existing_cols:
            raise ValueError(
                f"Column '{src_col}' does not exist in {target.schema}.{target.table}"
            )
    else:
        src_col = find_last_nonempty_column_ending_with_e(target)

    console.print(
        f"[green]Using source column:[/green] [bold]{src_col}[/bold]"
    )

    calculate_lith_fuzzy_match_percentages(
        target=target,
        src_col=src_col,
        threshold=threshold,
        row_copy_threshold_percent=row_copy_threshold_percent,
        limit=limit,
        dry_run=dry_run,
    )


@normalize_cli.command("find-last-e-column")
def normalize_find_last_e_column():
    """Print the last non-empty column ending with 'e'."""
    target = get_current_target()
    src_col = find_last_nonempty_column_ending_with_e(target)
    print(src_col)

@normalize_cli.command("find-second-last-e-column")
def normalize_find_second_last_e_column():
    """Print the second-last non-empty column ending with 'e'."""
    target = get_current_target()
    src_col = find_second_last_nonempty_column_ending_with_e(target)
    print(src_col)



@normalize_cli.command("match-remaining-cols")
def match_remaining_cols(
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
    target = get_current_target()
    existing_cols = get_existing_columns(target)

    non_age_col, columns_between, second_last_col = get_columns_between_non_age_and_second_last(
        target=target,
        non_age_col=non_age_col,
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

        response = Prompt.ask(
            "Would you like to merge into 'name'? [y/n, Enter to exit]",
            default="",
            show_default=False,
        ).strip().lower()

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

    response = Prompt.ask(
        "Would you like to merge the no columns elsewhere? [y/n]",
        default="n",
        show_default=False,
    ).strip().lower()

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



#____________________________BASH SCRIPTS POLYGONS_______________________________________

'''
--------------BULK UPDATE POLYGONS COMMANDS-------------------
slugs=(
japan_yoriiso
japan_yorii
japan_yonaizawa
japan_yokoyama
japan_yokota
japan_yokohama
)

for slug in "${slugs[@]}"; do
    macrostrat maps staging normalize set-map "$slug" >/dev/null
    macrostrat maps staging normalize set-layer polygons >/dev/null
    non_age_col=$(
      macrostrat maps staging normalize copy-age \
        --older legend03e --newer legend03e \
        --older legend02e --newer legend02e \
        --older legend01e --newer legend01e \
        --no-prompt \
      | tail -n 1
    )
    
    if [[ "$non_age_col" == "Finished copy-age" || -z "$non_age_col" ]]; then
        non_age_col="legend04e"
    fi
    
    last_col=$(macrostrat maps staging normalize find-last-e-column)
    
    macrostrat maps staging normalize copy-column \
    --src "$last_col" \
    --dst descrip \
    --no-prompt
    
    macrostrat maps staging normalize copy-orig-id \
    --src major_code
    
    macrostrat maps staging normalize copy-column \
    --src symbol \
    --dst unit_label \
    --no-prompt
    
    macrostrat maps staging normalize match-remaining-cols \
    "$non_age_col"
    
    macrostrat maps staging normalize fuzzy-match-lith \
    --src "$last_col"

done
'''





'''
BULK NULL POLYGON PREFERRED COLUMNS
slugs=(
japan_yunotsu_and_gotsu
japan_yotsuya
japan_yoshioka
japan_yoshino_yama
)

for slug in "${slugs[@]}"; do
    macrostrat maps staging normalize set-map "$slug" >/dev/null
    macrostrat maps staging normalize set-layer polygons >/dev/null
    macrostrat maps staging normalize null-column t_interval; \
    macrostrat maps staging normalize null-column b_interval; \
    macrostrat maps staging normalize null-column lith; \
    macrostrat maps staging normalize null-column age; \
    macrostrat maps staging normalize null-column descrip; \
    macrostrat maps staging normalize null-column name;
done


'''


#_______________________________BASH SCRIPTS LINES_______________________________

'''
--------------BULK UPDATE LINES COMMANDS-------------------
slugs=(
japan_yunotsu_and_gotsu
japan_yotsuya
japan_yoshioka
japan_yoshino_yama
japan_yoriiso
japan_yorii
japan_yonaizawa
japan_yokoyama
japan_yokota
japan_yokohama

)

for slug in "${slugs[@]}"; do
    macrostrat maps staging normalize set-map "$slug" >/dev/null
    macrostrat maps staging normalize set-layer lines >/dev/null
    
    macrostrat maps staging normalize copy-orig-id \
    --src major_code
    
    macrostrat maps staging normalize copy-column \
    --src legend01e \
    --dst type \
    --no-prompt
    
    macrostrat maps staging normalize copy-column \
    --src legend02e \
    --dst name \
    --no-prompt
    
    macrostrat maps staging normalize copy-column \
    --src descriptio \
    --dst descrip \
    --no-prompt
    
    macrostrat maps staging normalize merge-column \
    --src remarks \
    --dst descrip \
    --separator '; '

done
'''






#_______________________________BASH SCRIPTS POINTS___________________________________

'''
--------------BULK UPDATE POINTS COMMANDS-------------------
slugs=(
japan_yunotsu_and_gotsu
japan_yotsuya
japan_yoshioka
japan_yoshino_yama
japan_yoriiso
japan_yorii
japan_yonaizawa
japan_yokoyama
japan_yokota
japan_yokohama
)

for slug in "${slugs[@]}"; do
    macrostrat maps staging normalize set-map "$slug" >/dev/null
    macrostrat maps staging normalize set-layer points >/dev/null
    
    macrostrat maps staging normalize copy-orig-id \
    --src serial_no \
    --src no
    
    macrostrat maps staging normalize copy-column \
    --src legend01e \
    --dst point_type \
    --no-prompt
    
    macrostrat maps staging normalize copy-column \
    --src strike_val \
    --dst strike \
    --no-prompt
    
    macrostrat maps staging normalize copy-column \
    --src dip_value \
    --dst dip \
    --no-prompt
    
    macrostrat maps staging normalize copy-column \
    --src legend02e \
    --dst descrip \
    --no-prompt
    
    macrostrat maps staging normalize copy-column \
    --src remarks \
    --dst comments \
    --no-prompt
    
    macrostrat maps staging normalize merge-column \
    --src legend03e \
    --dst descrip \
    --separator "; "
done
'''