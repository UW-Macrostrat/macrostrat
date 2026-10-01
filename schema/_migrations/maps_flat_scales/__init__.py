"""One `maps.polygons`, one `maps.lines` and one `maps.lookup`, with `scale` an
ordinary column on each."""

import time
from pathlib import Path

from macrostrat.database import Database
from macrostrat.schema_management import Migration

__dir__ = Path(__file__).parent

_SCALES = ("tiny", "small", "medium", "large")


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


# SQLSTATEs a locking attempt may fail with and be retried: a deadlock chosen
# against us, and the lock timeout below.
_RETRY_STATES = {"40P01", "55P03"}
_LOCK_TIMEOUT = "60s"
_ATTEMPTS = 5


def _sqlstate(err: Exception) -> str | None:
    """psycopg 3 spells it `sqlstate`, psycopg 2 `pgcode`; both are installed."""
    orig = getattr(err, "orig", err)
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def _lock_statement(tables: list[str], mode: str) -> str:
    return "LOCK TABLE " + ", ".join(tables) + " IN " + mode + " MODE"


def run_locked(db: Database, sql: Path, *, exclusive: list[str], shared: list[str]):
    """Run `sql` as one transaction that takes every lock it will need first.

    A statement that locks a table halfway through a transaction, while readers
    are taking the same tables in their own order, is how the `DROP TABLE`s here
    deadlocked against the API. So the first statement locks everything the file
    touches: `exclusive` (ACCESS EXCLUSIVE, for what is dropped or rewritten) and
    `shared` (SHARE ROW EXCLUSIVE, what a new foreign key will reference). Readers
    already holding a table are waited out; new ones queue behind. A deadlock or
    a lock timeout there costs nothing yet, so it is simply tried again.
    """
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            with db.transaction():
                # `raise_errors` on every statement: `run_sql` otherwise prints an
                # error and carries on, and the transaction is then committed dead.
                db.run_sql(
                    f"SET LOCAL lock_timeout = '{_LOCK_TIMEOUT}'", raise_errors=True
                )
                if exclusive:
                    db.run_sql(
                        _lock_statement(exclusive, "ACCESS EXCLUSIVE"),
                        raise_errors=True,
                    )
                if shared:
                    db.run_sql(
                        _lock_statement(shared, "SHARE ROW EXCLUSIVE"),
                        raise_errors=True,
                    )
                db.run_sql(sql, raise_errors=True)
            return
        except Exception as err:
            if _sqlstate(err) not in _RETRY_STATES or attempt == _ATTEMPTS:
                raise
            print(
                f"Could not take the locks (attempt {attempt} of {_ATTEMPTS}):"
                f" {str(getattr(err, 'orig', err)).splitlines()[0]}. Trying again."
            )
            time.sleep(5 * attempt)


class _OneTransaction(Migration):
    """A migration whose SQL file runs as one transaction, so a failure anywhere
    leaves the database as it was."""

    subsystem = "maps"
    destructive = True
    readiness_state = "beta"
    load_sql_files = False
    sql_file: str
    # Locked before anything else runs; see `run_locked`.
    exclusive: list[str] = []
    shared: list[str] = []

    def before(self, db: Database):
        pass

    def after(self, db: Database):
        pass

    def apply(self, db: Database):
        self.before(db)
        run_locked(
            db, __dir__ / self.sql_file, exclusive=self.exclusive, shared=self.shared
        )
        self.after(db)


class _FlattenScales(_OneTransaction):
    """Merge a table's scale partitions into one table; see the SQL files."""

    # Rewrites the whole table (minutes, under an exclusive lock) and drops the
    # partitions once their rows are merged; nothing is lost, but it is a rewrite.
    sync_chunks = ["maps", "core", "map-topology", "permissions"]
    table: str

    def __init__(self):
        self.sql_file = f"{self.table}.sql"
        # The parent, its partitions, and the per-scale views re-pointed or
        # dropped along the way.
        self.exclusive = [f"maps.{self.table}"] + [
            f"maps.{self.table}_{s}" for s in _SCALES
        ]
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

    def __init__(self):
        super().__init__()
        self.exclusive += [f"maps.{s}" for s in _SCALES]
        # Gain a foreign key to the new table.
        self.shared = ["maps.map_legend", "maps.map_units", "maps.map_liths"]


class MapsLinesFlat(_FlattenScales):
    name = "maps-lines-flat"
    description = "The same for `maps.lines`; `line_ids` moves into the `maps` schema."
    depends_on = ["maps-polygons-flat"]
    table = "lines"

    def __init__(self):
        super().__init__()
        # Dropped with the parent (and restored by the sync).
        self.exclusive += [f"lines.{s}" for s in _SCALES] + ["tile_layers.map_lines"]


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
    exclusive = [f"public.lookup_{s}" for s in _SCALES]
    # Referenced by the new table's foreign keys.
    shared = ["maps.polygons", "maps.legend", "maps.sources"]

    preconditions = [
        lambda db: (
            _relkind(db, "maps", "polygons") == "r"
            and all(_relkind(db, "public", f"lookup_{s}") == "r" for s in _SCALES)
        )
    ]
    postconditions = [
        lambda db: (
            _relkind(db, "maps", "lookup") == "r"
            and all(_relkind(db, "public", f"lookup_{s}") == "v" for s in _SCALES)
        )
    ]

    def before(self, db: Database):
        self._rows = sum(
            db.run_query(f"SELECT count(*) FROM public.lookup_{s}").scalar()
            for s in _SCALES
        )

    def after(self, db: Database):
        kept = db.run_query("SELECT count(*) FROM maps.lookup").scalar()
        print(
            f"{kept} of {self._rows} lookup rows carried over; the rest had no"
            " polygon or duplicated a map_id and are rebuilt by processing."
        )
