"""One `maps.polygons` and one `maps.lines`, with `scale` an ordinary column."""

from pathlib import Path

from macrostrat.database import Database
from macrostrat.schema_management import Migration

__dir__ = Path(__file__).parent


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


def _is_partitioned(table: str):
    return lambda db: _relkind(db, "maps", table) == "p"


def _is_flat(table: str):
    """The table is ordinary and its largest former partition is a view."""
    return lambda db: (
        _relkind(db, "maps", table) == "r"
        and _relkind(db, "maps", f"{table}_large") == "v"
    )


def _require_btree_gist(db: Database):
    """The `(scale, geom)` index needs `btree_gist`, which only a superuser can
    create. Say so rather than failing a long transaction on the index step."""
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


class _FlattenScales(Migration):
    subsystem = "maps"
    # Rewrites the whole table (minutes, under an exclusive lock) and drops the
    # partitions once their rows are merged; nothing is lost, but it is a rewrite.
    destructive = True
    readiness_state = "beta"
    sync_chunks = ["maps", "core", "map-topology"]
    load_sql_files = False

    table: str

    def __init__(self):
        self.preconditions = [_is_partitioned(self.table)]
        self.postconditions = [_is_flat(self.table)]

    def apply(self, db: Database):
        _require_btree_gist(db)
        _report_cascade(db, f"maps.{self.table}")
        # One transaction: a failure anywhere leaves the partitioned table as it was.
        with db.transaction():
            db.run_sql(__dir__ / f"{self.table}.sql", raise_errors=True)


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
