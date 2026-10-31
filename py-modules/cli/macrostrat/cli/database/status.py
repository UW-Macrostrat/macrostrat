"""A read-only health report for a Postgres cluster.

Every default query reads catalog and statistics views, so the report costs about
a second whatever the data size. Size scans stat every file in the cluster and
run only when asked for.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.measure import Measurement
from rich.table import Table
from rich.text import Text
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError

__all__ = ["database_status"]

# Thresholds past which the report warns, and the command exits non-zero.
ARCHIVE_BACKLOG_SEGMENTS = 200
CONNECTION_FRACTION = 0.8
IDLE_IN_TRANSACTION = "15 minutes"
REPLICATION_LAG_BYTES = 1 << 30
XID_AGE = 1_000_000_000

SETTINGS = (
    "max_connections",
    "superuser_reserved_connections",
    "shared_buffers",
    "work_mem",
    "maintenance_work_mem",
    "max_wal_size",
    "wal_compression",
    "archive_mode",
    "temp_file_limit",
    "log_temp_files",
    "statement_timeout",
    "idle_in_transaction_session_timeout",
    "autovacuum_max_workers",
    "autovacuum_vacuum_cost_limit",
    "max_parallel_workers_per_gather",
)


@dataclass
class Report:
    conn: Connection
    console: Console
    warnings: list[str] = field(default_factory=list)

    def section(self, title: str):
        self.console.print(f"\n[bold]{title}[/]")

    def warn(self, message: str):
        self.warnings.append(message)
        self.console.print(f"[yellow]⚠ {escape(message)}[/]")

    def query(self, sql: str, **params):
        """Rows, or None with the error shown; some views need `pg_monitor`."""
        try:
            return self.conn.execute(text(sql), params).all()
        except DBAPIError as err:
            self.console.print(f"[dim]unavailable: {escape(str(err.orig).strip())}[/]")
            return None

    def table(self, rows, *, empty: str | None = None):
        """Print rows; columns named with a leading underscore are for checks only."""
        if not rows:
            if empty is not None:
                self.console.print(f"[dim]{empty}[/]")
            return
        columns = [c for c in rows[0]._fields if not c.startswith("_")]
        cells = [[_format(row._mapping[c]) for c in columns] for row in rows]
        table = Table(
            *(c.replace("_", " ") for c in columns), box=box.SIMPLE_HEAD, pad_edge=False
        )
        for row in cells:
            table.add_row(*map(escape, row))
        console = self.console
        unbounded = console.options.update_width(10_000)
        if Measurement.get(console, unbounded, table).maximum <= console.width:
            console.print(table)
            return
        # Too narrow for the table, which would cut values off: one line per row.
        for row in cells:
            console.print(_record(columns, row, console.width))


def _record(columns, values, width: int) -> Text:
    """A row as labelled values, breaking lines only between them."""
    line = Text("• ")
    used = 2
    for column, value in zip(columns, values):
        if not value:
            continue
        size = len(column) + 1 + len(value)
        if used > 2 and used + 2 + size > width:
            line.append("\n  ")
            used = 2
        elif used > 2:
            line.append("  ")
            used += 2
        line.append(column.replace("_", " "), style="dim")
        line.append(f" {value}")
        used += size
    return line


def _format(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, timedelta):
        return str(value - timedelta(microseconds=value.microseconds))
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def database_status(
    engine: Engine, console: Console, *, sizes: bool = False
) -> list[str]:
    """Print the report for `engine`'s cluster and return its warnings."""
    # Autocommit, so a view the role cannot read fails alone.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        report = Report(conn, console)
        # Read before this session's own timeout shadows the configured one.
        settings = _settings(report)
        conn.execute(text("SET statement_timeout = '15s'"))
        _server(report)
        _connections(report)
        _transactions(report)
        _wal(report)
        _replication(report)
        _in_progress(report)
        _databases(report)
        _tables(report)
        if sizes:
            conn.execute(text("SET statement_timeout = '5min'"))
            _sizes(report)
        report.section("Settings")
        report.table(settings)
    return report.warnings


def _server(r: Report):
    r.section("Server")
    r.table(
        r.query(
            """
            SELECT current_setting('server_version') AS version,
                   current_database() AS database, current_user AS role,
                   pg_is_in_recovery() AS replica,
                   date_trunc('second', now() - pg_postmaster_start_time()) AS uptime
            """
        )
    )
    # A new timeline means a failover.
    r.table(r.query("SELECT timeline_id AS timeline FROM pg_control_checkpoint()"))


def _connections(r: Report):
    r.section("Connections")
    rows = r.query(
        """
        SELECT count(*) AS used,
               current_setting('max_connections')::int
                 - current_setting('superuser_reserved_connections')::int AS available,
               count(*) FILTER (WHERE starts_with(state, 'idle in transaction'))
                 AS idle_in_transaction
        FROM pg_stat_activity WHERE backend_type = 'client backend'
        """
    )
    r.table(rows)
    if rows and rows[0].used > CONNECTION_FRACTION * rows[0].available:
        r.warn(
            f"{rows[0].used} of {rows[0].available} connections in use; "
            "parallel workers fail once these run out"
        )
    r.table(
        r.query(
            """
            SELECT coalesce(nullif(application_name, ''), '(none)') AS application,
                   usename AS role, datname AS database, count(*) AS total,
                   count(*) FILTER (WHERE state = 'active') AS active,
                   count(*) FILTER (WHERE state = 'idle') AS idle,
                   count(*) FILTER (WHERE starts_with(state, 'idle in transaction'))
                     AS in_transaction
            FROM pg_stat_activity WHERE backend_type = 'client backend'
            GROUP BY 1, 2, 3 ORDER BY total DESC LIMIT 15
            """
        )
    )


def _transactions(r: Report):
    r.section("Transactions open over 5 minutes")
    rows = r.query(
        """
        SELECT pid, application_name AS application, state,
               date_trunc('second', now() - xact_start) AS age,
               wait_event, left(regexp_replace(query, '\\s+', ' ', 'g'), 80) AS query,
               starts_with(state, 'idle in transaction')
                 AND now() - state_change > CAST(:idle AS interval) AS _stale
        FROM pg_stat_activity
        WHERE backend_type = 'client backend' AND pid <> pg_backend_pid()
          AND xact_start < now() - interval '5 minutes'
        ORDER BY xact_start LIMIT 15
        """,
        idle=IDLE_IN_TRANSACTION,
    )
    r.table(rows, empty="none")
    stale = [row.pid for row in rows or [] if row._stale]
    if stale:
        r.warn(
            f"idle in a transaction for over {IDLE_IN_TRANSACTION}: pids "
            + ", ".join(map(str, stale))
        )

    blocked = r.query(
        """
        SELECT pid, pg_blocking_pids(pid) AS blocked_by,
               date_trunc('second', now() - query_start) AS waiting,
               left(regexp_replace(query, '\\s+', ' ', 'g'), 80) AS query
        FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0
        """
    )
    if blocked:
        r.section("Blocked sessions")
        r.table(blocked)


def _wal(r: Report):
    r.section("WAL and archiving")
    rows = r.query(
        """
        SELECT pg_size_pretty(sum(size)) AS wal_directory, count(*) AS segments,
               (SELECT count(*) FROM pg_ls_archive_statusdir()
                 WHERE right(name, 6) = '.ready') AS waiting_to_archive,
               current_setting('archive_mode') AS archive_mode
        FROM pg_ls_waldir()
        """
    )
    r.table(rows)
    if rows and rows[0].waiting_to_archive > ARCHIVE_BACKLOG_SEGMENTS:
        r.warn(
            f"{rows[0].waiting_to_archive} WAL segments waiting to archive; "
            "they stay on disk until archived"
        )

    archiver = r.query(
        """
        SELECT archived_count AS archived,
               date_trunc('second', now() - last_archived_time) AS since_last,
               failed_count AS failed, last_failed_wal,
               coalesce(last_failed_time > last_archived_time, false) AS _failing
        FROM pg_stat_archiver
        """
    )
    r.table(archiver)
    if archiver and archiver[0]._failing:
        r.warn(f"archiving is failing, last at {archiver[0].last_failed_wal}")

    r.table(
        r.query(
            """
            SELECT pg_size_pretty(w.wal_bytes) AS wal_written,
                   pg_size_pretty((w.wal_bytes / greatest(
                     extract(epoch FROM now() - w.stats_reset), 1) * 3600)::bigint)
                     AS per_hour,
                   w.wal_fpi AS full_page_images,
                   b.checkpoints_timed, b.checkpoints_req AS checkpoints_forced,
                   w.stats_reset
            FROM pg_stat_wal w, pg_stat_bgwriter b
            """
        )
    )


def _replication(r: Report):
    replicas = r.query(
        """
        SELECT application_name AS replica, state, sync_state,
               pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn))
                 AS behind,
               replay_lag,
               pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS _behind_bytes
        FROM pg_stat_replication
        """
    )
    slots = r.query(
        """
        SELECT slot_name AS slot, active,
               pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn))
                 AS retained
        FROM pg_replication_slots
        """
    )
    if not replicas and not slots:
        return
    r.section("Replication")
    r.table(replicas)
    for row in replicas or []:
        if (row._behind_bytes or 0) > REPLICATION_LAG_BYTES:
            r.warn(f"replica {row.replica} is {row.behind} behind")
    r.table(slots)
    for row in slots or []:
        if not row.active:
            r.warn(f"inactive replication slot {row.slot} retains {row.retained}")


def _in_progress(r: Report):
    queries = {
        "Vacuums": """
            SELECT p.pid, p.datname AS database, p.relid::regclass AS relation,
                   p.phase, round(100.0 * p.heap_blks_scanned
                     / nullif(p.heap_blks_total, 0), 1) AS percent_scanned,
                   date_trunc('second', now() - a.xact_start) AS running
            FROM pg_stat_progress_vacuum p JOIN pg_stat_activity a USING (pid)
            """,
        "Index builds": """
            SELECT pid, datname AS database, relid::regclass AS relation, command,
                   phase
            FROM pg_stat_progress_create_index
            """,
        "COPY": """
            SELECT pid, datname AS database, relid::regclass AS relation, command,
                   pg_size_pretty(bytes_processed) AS processed,
                   tuples_processed AS rows
            FROM pg_stat_progress_copy
            """,
    }
    for title, sql in queries.items():
        rows = r.query(sql)
        if rows:
            r.section(f"{title} in progress")
            r.table(rows)


def _databases(r: Report):
    r.section("Databases")
    rows = r.query(
        """
        SELECT d.datname AS database, age(d.datfrozenxid) AS xid_age,
               s.numbackends AS connections,
               pg_size_pretty(s.temp_bytes) AS temp_spilled, s.deadlocks,
               s.stats_reset
        FROM pg_database d JOIN pg_stat_database s ON s.datid = d.oid
        WHERE d.datallowconn
          AND (s.numbackends > 0 OR s.temp_bytes > 0 OR s.deadlocks > 0)
        ORDER BY s.temp_bytes DESC
        """
    )
    r.table(rows)
    old = r.query(
        """
        SELECT datname AS database, age(datfrozenxid) AS xid_age FROM pg_database
        WHERE age(datfrozenxid) > :limit
        """,
        limit=XID_AGE,
    )
    for row in old or []:
        r.warn(
            f"{row.database} is {row.xid_age:,} transactions from its last "
            "freeze; wraparound stops writes at 2 billion"
        )


def _tables(r: Report):
    r.section("Most dead rows in this database")
    r.table(
        r.query(
            """
            SELECT schemaname || '.' || relname AS relation, n_live_tup AS live,
                   n_dead_tup AS dead, last_autovacuum, last_autoanalyze
            FROM pg_stat_all_tables WHERE n_dead_tup > 0
            ORDER BY n_dead_tup DESC LIMIT 10
            """
        ),
        empty="none",
    )


def _sizes(r: Report):
    r.section("Database sizes")
    r.table(
        r.query(
            """
            WITH sizes AS MATERIALIZED (
              SELECT datname, pg_database_size(datname) AS bytes
              FROM pg_database WHERE datallowconn
            )
            (SELECT datname AS database, pg_size_pretty(bytes) AS size
             FROM sizes ORDER BY bytes DESC)
            UNION ALL
            SELECT '(all)', pg_size_pretty(sum(bytes)) FROM sizes
            """
        )
    )
    r.section("Largest relations in this database")
    r.table(
        r.query(
            """
            SELECT n.nspname || '.' || c.relname AS relation,
                   pg_size_pretty(pg_total_relation_size(c.oid)) AS total
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'm', 'p')
            ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 15
            """
        )
    )


def _settings(r: Report):
    return r.query(
        """
        SELECT name, current_setting(name) AS value, source
        FROM pg_settings WHERE name = ANY(:names) ORDER BY name
        """,
        names=list(SETTINGS),
    )
