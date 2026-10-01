"""One `maps.polygons`, one `maps.lines` and one `maps.lookup`, with `scale` an
ordinary column on each."""

from pathlib import Path

from macrostrat.database import Database
from macrostrat.schema_management import Migration

__dir__ = Path(__file__).parent

_LOOKUP_SCALES = ("tiny", "small", "medium", "large")


def _relkind(db: Database, schema: str, name: str) -> str | None:
    """`p` partitioned, `r` ordinary table, `v` view, None when absent."""
    return db.run_query(
        """
        SELECT c.relkind FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = :schema AND c.relname = :name
        """,
        dict(schema=schema, name=name),
    ).scalar()


def _ensure_btree_gist(db: Database):
    """The `(scale, geom)` indexes need `btree_gist`. `0000-globals.sql` creates
    it on a fresh database; on an existing one this creates it when the
    migrating role may, and otherwise says what to run rather than failing a
    long transaction at the index step."""
    db.run_sql("CREATE EXTENSION IF NOT EXISTS btree_gist", raise_errors=False)
    if not db.run_query(
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gist')"
    ).scalar():
        raise RuntimeError(
            "The btree_gist extension is required; as a superuser run"
            " CREATE EXTENSION btree_gist; and apply again"
        )


def _report_cascade(db: Database, table: str):
    """Name the objects the parent takes with it, so the chunk sync's job is visible."""
    rows = db.run_query(
        """
        SELECT DISTINCT dep.relkind, dep.oid::regclass::text AS name
        FROM pg_depend d
        JOIN pg_rewrite rw ON d.classid = 'pg_rewrite'::regclass AND rw.oid = d.objid
        JOIN pg_class dep ON dep.oid = rw.ev_class
        WHERE d.refobjid = CAST(:table AS regclass) AND dep.oid <> d.refobjid
        UNION ALL
        SELECT 'f', p.oid::regprocedure::text
        FROM pg_depend d
        JOIN pg_proc p ON d.classid = 'pg_proc'::regclass AND p.oid = d.objid
        WHERE d.refclassid = 'pg_type'::regclass
          AND d.refobjid = (SELECT reltype FROM pg_class WHERE oid = CAST(:table AS regclass))
        ORDER BY 1, 2
        """,
        dict(table=table),
    ).all()
    if rows:
        print(f"Dropping {table} takes with it, to be restored by the chunk sync:")
        for r in rows:
            print(f"  - {r.name}")


class _OneTransaction(Migration):
    """A migration whose SQL file runs as one transaction, so a failure anywhere
    leaves the database as it was."""

    subsystem = "maps"
    destructive = True
    readiness_state = "beta"
    load_sql_files = False
    sql_file: str

    def before(self, db: Database):
        pass

    def after(self, db: Database):
        pass

    def apply(self, db: Database):
        self.before(db)
        with db.transaction():
            db.run_sql(__dir__ / self.sql_file, raise_errors=True)
        self.after(db)


class _FlattenScales(_OneTransaction):
    """Merge a table's scale partitions into one table; see the SQL files."""

    # Rewrites the whole table (minutes, under an exclusive lock) and drops the
    # partitions once their rows are merged; nothing is lost, but it is a rewrite.
    sync_chunks = ["maps", "core", "map-topology", "permissions"]
    table: str

    def __init__(self):
        self.sql_file = f"{self.table}.sql"
        self.preconditions = [lambda db: _relkind(db, "maps", self.table) == "p"]
        self.postconditions = [
            lambda db: (
                _relkind(db, "maps", self.table) == "r"
                and _relkind(db, "maps", f"{self.table}_large") == "v"
            )
        ]

    def before(self, db: Database):
        _ensure_btree_gist(db)
        _report_cascade(db, f"maps.{self.table}")


class MapsPolygonsFlat(_FlattenScales):
    name = "maps-polygons-flat"
    description = """
    Replace the scale-partitioned `maps.polygons` with one table: `PRIMARY KEY
    (map_id)`, a `(scale, geom)` index in place of partition pruning, the former
    partitions as writable views, one `map_ids` sequence, and the foreign keys
    from `map_legend`, `map_units` and `map_liths` that partitioning forbade.
    """
    table = "polygons"


class MapsLinesFlat(_FlattenScales):
    name = "maps-lines-flat"
    description = "The same for `maps.lines`; `line_ids` moves into the `maps` schema."
    depends_on = ["maps-polygons-flat"]
    table = "lines"


class MapsLookupUnified(_OneTransaction):
    name = "maps-lookup-unified"
    description = """
    Replace the four `public.lookup_<scale>` tables with `maps.lookup`, keyed on
    `map_id` and referencing `maps.polygons` and `maps.legend`; the old names
    stay as writable views.
    """
    depends_on = ["maps-polygons-flat"]
    sync_chunks = ["maps", "permissions"]
    sql_file = "lookup.sql"

    preconditions = [
        lambda db: (
            _relkind(db, "maps", "polygons") == "r"
            and all(
                _relkind(db, "public", f"lookup_{s}") == "r" for s in _LOOKUP_SCALES
            )
        )
    ]
    postconditions = [
        lambda db: (
            _relkind(db, "maps", "lookup") == "r"
            and all(
                _relkind(db, "public", f"lookup_{s}") == "v" for s in _LOOKUP_SCALES
            )
        )
    ]

    def before(self, db: Database):
        self._rows = sum(
            db.run_query(f"SELECT count(*) FROM public.lookup_{s}").scalar()
            for s in _LOOKUP_SCALES
        )

    def after(self, db: Database):
        kept = db.run_query("SELECT count(*) FROM maps.lookup").scalar()
        print(
            f"{kept} of {self._rows} lookup rows carried over; the rest had no"
            " polygon or duplicated a map_id and are rebuilt by processing."
        )
