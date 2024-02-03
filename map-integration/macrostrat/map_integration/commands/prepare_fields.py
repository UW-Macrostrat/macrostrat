from pathlib import Path

from psycopg2.sql import SQL, Identifier
from rich import print
from sqlalchemy.exc import NoResultFound, NoSuchTableError
from typer import Argument, Option

from ..database import db
from ..utils import column_exists, create_sources_record, get_map_info, table_exists


def prepare_fields(
    identifier: str = Argument(None),
    all: bool = False,
    recover: bool = Option(False, "--recover", help="Recover sources records"),
):
    """Prepare empty fields for manual cleaning."""
    if all:
        prepare_fields_for_all_sources(recover=recover)
        return

    if identifier is None:
        raise ValueError("You must specify a slug or pass --all")

    _prepare_fields(identifier, recover=recover)


def _recover_sources_row(identifier):
    print(
        f"[bold yellow]Attempting to recover source record for [bold cyan]{identifier}"
    )
    try:
        return create_sources_record(db, identifier)
    except ValueError:
        print(f"[bold red]Failed to recover source record for [bold cyan]{identifier}")


def _prepare_fields(identifier: str, recover: bool = False):
    """Prepare empty fields for manual cleaning."""

    print(f"[bold]Preparing fields for source [cyan]{identifier}")

    schema = "sources"
    info = None
    try:
        info = get_map_info(db, identifier)
    except NoResultFound:
        print(f"[bold red]No source found with slug [bold cyan]{identifier}")
        print(
            f"[gray dim]Use [bold]--recover[/] to attempt to recover the record in the [bold]maps.sources[/] table."
        )
        if recover:
            info = _recover_sources_row(identifier)
    if info is None:
        print()
        return

    slug = info.slug
    source_id = info.id

    # The old format didn't specify the 'polygons' suffix
    # but the new one does.
    try:
        PolygonTableUpdater(db, f"{slug}_polygons", schema).run(source_id)
    except NoSuchTableError:
        print(f"[bold orange]No polygons table found for [bold cyan]{slug}")

    try:
        LineworkTableUpdater(db, f"{slug}_lines", schema).run(source_id)
    except NoSuchTableError:
        print(f"[bold orange]No lines table found for [bold cyan]{slug}")

    try:
        PointsTableUpdater(db, f"{slug}_points", schema).run(source_id)
    except NoSuchTableError:
        print(f"[bold orange]No points table found for [bold cyan]{slug}")

    print(
        f"\n[bold green]Source [bold cyan]{slug}[green] prepared for manual cleaning!\n"
    )


def prepare_fields_for_all_sources(recover=False):
    # Run prepare fields for all legacy map tables that don't have a _pkid column
    sql = Path(__file__).parent.parent / "procedures" / "all-candidate-source-slugs.sql"
    for table in db.run_query(sql):
        prepare_fields(table.slug, recover=recover)


def get_sources_record(slug):
    """Insert a record into the sources table."""
    return db.run_query(
        """
        INSERT INTO maps.sources (slug)
        VALUES (:source_name)
        ON CONFLICT (slug)
        DO NOTHING
        RETURNING source_id
        """,
        dict(source_name=slug),
    ).scalar()


common_columns = {
    "source_id": "integer",
    "orig_id": "integer",
    "omit": "boolean",
    # "ready": "boolean",  # Ready to be inserted?
}


class SourcesTableUpdater:
    """Base class to bring a points, lines, or polygons sources table to the current standard."""

    column_spec = {}

    def __init__(self, db, table_name, schema=None):
        if schema is None:
            schema = "sources"
        self._table_name = table_name
        self._schema = schema
        self.db = db
        self._table = Identifier(schema, table_name)

        # Check if the table exists
        if not self._exists():
            raise NoSuchTableError(f"Table {self._table} does not exist")

    def _column_exists(self, column_name):
        return column_exists(
            self.db, self._table_name, column_name, schema=self._schema
        )

    def _run_sql(self, sql, params=None):
        if params is None:
            params = {}
        params["table"] = self._table
        return self.db.run_sql(sql, params)

    def _exists(self):
        return table_exists(self.db, self._table_name, schema=self._schema)

    def _apply_column_mapping(self, columns, rename_geometry=True):
        sql = "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {type}"
        for name, type in columns.items():
            self._run_sql(
                sql, dict(table=self._table, column=Identifier(name), type=SQL(type))
            )

        # Rename the geometry column if necessary
        if not rename_geometry:
            return

        _has_geometry = self._column_exists("geometry")
        _has_geom = self._column_exists("geom")

        if _has_geometry and not _has_geom:
            self._run_sql(
                "ALTER TABLE {table} RENAME COLUMN geometry TO geom",
                dict(table=self._table),
            )

    def _set_source_id(self, source_id):
        self._run_sql(
            "UPDATE {table} SET source_id = :source_id",
            dict(source_id=source_id),
        )

    def _add_primary_key_column(self, column_name="_pkid"):
        self._run_sql(
            "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} SERIAL PRIMARY KEY",
            dict(column=Identifier(column_name)),
        )

    def add_columns(self):
        self._apply_column_mapping(self.column_spec)

    def run(self, source_id):
        self.add_columns()
        self._add_primary_key_column()
        self._set_source_id(source_id)


class PolygonTableUpdater(SourcesTableUpdater):
    column_spec = {
        **common_columns,
        "name": "text",
        "strat_name": "text",
        "age": "text",
        "lith": "text",
        "descrip": "text",
        "comments": "text",
        "t_interval": "integer",
        "b_interval": "integer",
    }

    def _update_legacy_polygon_columns(self):
        """Legacy tables had different standard names for several columns."""

        if self._column_exists("gid"):
            self._run_sql(
                "ALTER TABLE {table} RENAME COLUMN gid TO _pkid",
            )

        if self._column_exists("late_id") or self._column_exists("early_id"):
            self._run_sql(
                "UPDATE {table} SET  t_interval = late_id, b_interval = early_id",
            )

        if self._column_exists("ready"):
            self._run_sql(
                "UPDATE {table} SET omit = not ready WHERE ready IS NOT NULL",
            )

    def run(self, source_id):
        super().run(source_id)
        self._update_legacy_polygon_columns()


class LineworkTableUpdater(SourcesTableUpdater):
    column_spec = {
        **common_columns,
        "descrip": "text",
        "name": "character varying(255)",
        "type": "character varying(100)",
        "direction": "character varying(20)",
    }


class PointsTableUpdater(SourcesTableUpdater):
    column_spec = {
        **common_columns,
        "comments": "text",
        "strike": "integer",
        "dip": "integer",
        "dip_dir": "integer",
        "point_type": "character varying(100)",
        "certainty": "character varying(100)",
    }
