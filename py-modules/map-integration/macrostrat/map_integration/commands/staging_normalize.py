from dataclasses import dataclass

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


def copy_column_values(
    target: TableTarget,
    src: str,
    dst: str,
    dry_run: bool = False,
):
    """Copies all values from column `src` into column `dst` in the target table, overwriting any existing
    destination values. Validates that both columns exist before executing. When dry_run is True, the operation is
    described but not executed."""
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
        console.print("[green]Dry run only; no changes applied[/green]")
        return
    db.run_sql(
        "UPDATE {table} SET {dst} = {src}",
        dict(
            table=target.fq_identifier,
            src=Identifier(src),
            dst=Identifier(dst),
        ),
    )
    console.print(
        f"[green]Done:[/green] copied all values from {src} to {dst} "
        f"in {target.schema}.{target.table}"
    )


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
            "SELECT count(*) FROM {table} WHERE point_type IS NULL",
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
                    point_id AS mapped_id
                FROM maps.points
                WHERE point_type IS NOT NULL
                ORDER BY lower(trim(point_type::text)), point_id
            ),
            mapped AS (
                SELECT
                    t._pkid,
                    pl.mapped_id
                FROM {table} AS t
                LEFT JOIN point_lookup AS pl
                    ON lower(trim(nullif(t.point_type::text, ''))) = pl.type_key
            )
            UPDATE {table} AS t
            SET point_type = mapped.mapped_id
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
                    point_id AS mapped_id
                FROM maps.points
                WHERE point_type IS NOT NULL
                ORDER BY lower(trim(point_type::text)), point_id
            )
            UPDATE {table} AS t
            SET point_type = pl.mapped_id
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
        "SELECT count(*) FROM {table} WHERE point_type IS NULL",
        dict(table=target.fq_identifier),
    ).scalar()
    console.print(
        f"[green]Done:[/green] mapped integer IDs from {src_col}. "
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
            "SELECT count(*) FROM {table} WHERE type IS NULL",
            dict(table=target.fq_identifier),
        ).scalar()
        console.print("[green]Dry run only; no changes applied[/green]")
        return remaining_nulls

    if src_col == "type":
        db.run_sql(
            """
            WITH line_lookup AS (
                SELECT DISTINCT ON (lower(trim(type::text)))
                    lower(trim(type::text)) AS type_key,
                    line_id AS mapped_id
                FROM maps.lines
                WHERE type IS NOT NULL
                ORDER BY lower(trim(type::text)), line_id
            ),
            mapped AS (
                SELECT
                    t._pkid,
                    ll.mapped_id
                FROM {table} AS t
                LEFT JOIN line_lookup AS ll
                    ON lower(trim(nullif(t.type::text, ''))) = ll.type_key
            )
            UPDATE {table} AS t
            SET type = mapped.mapped_id
            FROM mapped
            WHERE t._pkid = mapped._pkid
            """,
            dict(table=target.fq_identifier),
        )
    else:
        db.run_sql(
            """
            WITH line_lookup AS (
                SELECT DISTINCT ON (lower(trim(type::text)))
                    lower(trim(type::text)) AS type_key,
                    line_id AS mapped_id
                FROM maps.lines
                WHERE type IS NOT NULL
                ORDER BY lower(trim(type::text)), line_id
            )
            UPDATE {table} AS t
            SET type = ll.mapped_id
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
        "SELECT count(*) FROM {table} WHERE type IS NULL",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[green]Done:[/green] mapped integer IDs from {src_col}. "
        f"Remaining null type rows: {remaining_nulls}"
    )
    return remaining_nulls


def copy_age_columns(
    target: TableTarget,
    older_col: str,
    newer_col: str,
    dry_run: bool = False,
):
    """Copies an older and a newer age column into b_interval and t_interval respectively, resolving interval
    names via macrostrat.intervals. If either side is null, the non-null value is used for both columns.
    Raises a ValueError if any required source or destination columns are missing."""
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
    if dry_run:
        console.print("[green]Dry run only; no changes applied[/green]")
        return
    db.run_sql(
        """
        WITH interval_lookup AS (
            SELECT lower(trim(interval_name)) AS interval_name, min(id) AS id
            FROM macrostrat.intervals
            GROUP BY 1
        ),
        mapped AS (
            SELECT
                t._pkid,
                old_il.id AS older_id,
                new_il.id AS newer_id
            FROM {table} AS t
            LEFT JOIN interval_lookup AS old_il
                ON old_il.interval_name = lower(trim(nullif({older_col}::text, '')))
            LEFT JOIN interval_lookup AS new_il
                ON new_il.interval_name = lower(trim(nullif({newer_col}::text, '')))
        )
        UPDATE {table} AS t
        SET
            b_interval = COALESCE(mapped.older_id, mapped.newer_id),
            t_interval = COALESCE(mapped.newer_id, mapped.older_id)
        FROM mapped
        WHERE t._pkid = mapped._pkid
        """,
        dict(
            table=target.fq_identifier,
            older_col=Identifier(older_col),
            newer_col=Identifier(newer_col),
        ),
    )
    console.print(
        f"[green]Done:[/green] populated b_interval and t_interval in "
        f"{target.schema}.{target.table}"
    )


normalize_cli = IngestionCLI(
    no_args_is_help=True,
    help="Normalize or bulk-fix staged table data.",
)


# ____________________________________CLI COMMANDS________________________________________________


@normalize_cli.command("copy-column")
def normalize_copy_column(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    src: str = Option(..., "--src", help="Source column to copy from"),
    dst: str = Option(..., "--dst", help="Destination column to overwrite"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Copy all values from one column into another column, overwriting destination values.
    """
    target = TableTarget(schema=schema, table=table)
    copy_column_values(target=target, src=src, dst=dst, dry_run=dry_run)


@normalize_cli.command("copy-preferred-columns")
def normalize_copy_preferred_columns(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively map source columns into the preferred destination columns for
    points, lines, or polygons tables. Press Enter to skip a destination field.
    """
    target = TableTarget(schema=schema, table=table)
    copy_preferred_column_values_interactive(
        target=target,
        dry_run=dry_run,
    )


@normalize_cli.command("add-preferred-columns")
def normalize_add_preferred_columns(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Add any missing preferred standard columns for a points, lines, or polygons
    staging table. Existing columns are skipped.
    """
    target = TableTarget(schema=schema, table=table)
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


@normalize_cli.command("calculate-age")
def normalize_calculate_age(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    col_one: str = Option(..., "--col-one", help="Primary age source column"),
    col_two: str = Option(..., "--col-two", help="Secondary age source column"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Populate b_interval and t_interval using two user-provided columns,
    falling back to era when present.
    """
    target = TableTarget(schema=schema, table=table)
    calculate_age_intervals(
        target=target,
        col_one=col_one,
        col_two=col_two,
        dry_run=dry_run,
    )


@normalize_cli.command("copy-ages")
def normalize_copy_ages(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    older_col: str = Option(..., "--older-col", help="Column containing older age"),
    newer_col: str = Option(..., "--newer-col", help="Column containing younger age"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Copy older/newer age columns into b_interval and t_interval.
    If either side is null, use whichever column contains data for both.
    """
    target = TableTarget(schema=schema, table=table)
    copy_age_columns(
        target=target,
        older_col=older_col,
        newer_col=newer_col,
        dry_run=dry_run,
    )


@normalize_cli.command("copy-line-type")
def normalize_copy_line_type(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    src: str = Option(..., "--src", help="Initial source column to map from"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Map a source column into the linework type column using values from maps.lines.
    If nulls remain in type after a pass, the user is prompted to map another column.
    Press Enter to stop.
    """
    target = TableTarget(schema=schema, table=table)

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
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    src: str = Option(..., "--src", help="Initial source column to map from"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Map a source column into the point_type column using values from maps.points.
    If nulls remain in point_type after a pass, the user is prompted to map another column.
    Press Enter to stop.
    """
    target = TableTarget(schema=schema, table=table)
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
