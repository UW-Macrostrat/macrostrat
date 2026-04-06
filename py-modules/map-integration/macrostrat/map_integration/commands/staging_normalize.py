from dataclasses import dataclass

from rich.console import Console
from rich.prompt import Prompt
from typer import Argument, Option
from psycopg2.sql import SQL, Identifier

from macrostrat.map_integration.commands.prepare_fields.utils import (
    LineworkTableUpdater,
    PointsTableUpdater,
    PolygonTableUpdater,
)
from macrostrat.map_integration.database import get_database
from macrostrat.map_integration.utils import IngestionCLI

console = Console()

'''
Future subcommands to add
fill-null
rename-values
trim-whitespace
lowercase-column
coalesce-columns
'''


@dataclass(frozen=True)
class TableTarget:
    schema: str
    table: str

    @property
    def fq_identifier(self):
        return Identifier(self.schema, self.table)

def get_integer_required_fields_for_table(table: str) -> set[str]:
    required_fields = get_required_fields_for_table(table)
    integer_types = {"integer", "bigint", "serial", "bigserial"}

    out = set()
    for col_name, col_type in required_fields.items():
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


def get_required_fields_for_table(table: str) -> dict[str, str]:
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

def add_required_columns(
    target: TableTarget,
    dry_run: bool = False,
):
    db = get_database()
    existing_cols = get_existing_columns(target)
    required_spec = get_required_fields_for_table(target.table)
    console.print(
        f"[blue]Checking required columns for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold]"
    )
    for col_name, col_type in required_spec.items():
        if col_name in existing_cols:
            console.print(
                f"[yellow]Skipping[/yellow] [bold]{col_name}[/bold]: already exists"
            )
            continue
        console.print(
            f"[blue]Adding[/blue] [bold]{col_name}[/bold] "
            f"[dim]({col_type})[/dim]"
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
        console.print("[green]Done:[/green] required columns check/add complete")


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


def copy_required_column_values_interactive(
    target: TableTarget,
    dry_run: bool = False,
):
    db = get_database()
    required_fields = get_required_fields_for_table(target.table)
    existing_cols = get_existing_columns(target)
    integer_dest_fields = get_integer_required_fields_for_table(target.table)

    row_count = db.run_query(
        "SELECT count(*) FROM {table}",
        dict(table=target.fq_identifier),
    ).scalar()

    console.print(
        f"[blue]Preparing interactive required-field mapping for[/blue] "
        f"[bold]{target.schema}.{target.table}[/bold] "
        f"across {row_count} rows"
    )
    console.print(
        f"[dim]Available columns:[/dim] {', '.join(sorted(existing_cols))}"
    )

    for dst in required_fields:
        src = Prompt.ask(
            f"Map source column to required destination column [bold]{dst}[/bold] "
            f"(press Enter to skip)",
            default="",
            show_default=False,
        ).strip()

        if src == "":
            console.print(
                f"[yellow]Skipping[/yellow] destination [bold]{dst}[/bold]"
            )
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
        console.print("[green]Done:[/green] interactive required-field copy complete")


normalize_cli = IngestionCLI(
    no_args_is_help=True,
    help="Normalize or bulk-fix staged table data.",
)



#____________________________________CLI COMMANDS________________________________________________

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


@normalize_cli.command("copy-required-columns")
def normalize_copy_required_columns(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Interactively map source columns into the required destination columns for
    points, lines, or polygons tables. Press Enter to skip a destination field.
    """
    target = TableTarget(schema=schema, table=table)
    copy_required_column_values_interactive(
        target=target,
        dry_run=dry_run,
    )


@normalize_cli.command("add-required-columns")
def normalize_add_required_columns(
    schema: str = Argument(..., help="Schema name"),
    table: str = Argument(..., help="Table name"),
    dry_run: bool = Option(False, "--dry-run", help="Preview only"),
):
    """
    Add any missing required standard columns for a points, lines, or polygons
    staging table. Existing columns are skipped.
    """
    target = TableTarget(schema=schema, table=table)
    add_required_columns(target=target, dry_run=dry_run)