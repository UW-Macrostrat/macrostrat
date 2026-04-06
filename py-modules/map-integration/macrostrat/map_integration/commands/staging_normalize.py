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
    schema: str
    table: str

    @property
    def fq_identifier(self):
        return Identifier(self.schema, self.table)


def get_integer_preferred_fields_for_table(table: str) -> set[str]:
    preferred_fields = get_preferred_fields_for_table(table)
    integer_types = {"integer", "bigint", "serial", "bigserial"}

    out = set()
    for col_name, col_type in preferred_fields.items():
        normalized = col_type.strip().lower()
        if any(t in normalized for t in integer_types):
            out.add(col_name)

    return out


def validate_identifier(value: str, label: str) -> str:
    value = value.strip()
    if value == "":
        raise ValueError(f"{label} cannot be empty")
    return value


def get_existing_columns(target: TableTarget) -> set[str]:
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
