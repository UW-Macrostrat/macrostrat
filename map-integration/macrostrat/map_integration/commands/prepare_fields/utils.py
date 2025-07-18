from psycopg2.sql import SQL, Identifier
from sqlalchemy.exc import NoSuchTableError

from ...utils import column_exists, table_exists

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
        "color": "text",
        "strat_symbol": "text",
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
