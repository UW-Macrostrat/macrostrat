"""Import the pre-switchover tileserver lineage into `usage_stats`.

Tile requests from 2018 to March 2026 were counted by the legacy tileserver into
a standalone `tileserver_stats` database, one per environment. Those counts
predate the access-log dumps, so they cannot be re-harvested: they are copied
from that database as the `new_system = false` lineage of
`usage_stats.tileserver_{day,location}_index`.

The source is only read, so it stays intact as the cold backup. Rows are
inserted with `ON CONFLICT DO NOTHING` on each table's unique key, so a re-run
adds nothing, and a database that already holds the lineage (moved in by the
`usage-stats-consolidation` migration) is left as it is. Wrap the call in
`target.transaction()` to make it all-or-nothing.
"""

from dataclasses import dataclass

#: Columns copied per table. The target's other key columns (`new_system`,
#: `is_bot`, `x_cache`, `x_tile_cache`) take their defaults, which are the
#: values that mark the legacy lineage.
TABLES = {
    "day_index": (
        "tileserver_day_index",
        ["layer", "ext", "referrer", "app", "app_version", "date", "num_requests"],
    ),
    "location_index": (
        "tileserver_location_index",
        ["layer", "ext", "x", "y", "z", "orig_z", "num_requests"],
    ),
}

#: Array types for unnest(), so each batch is a single INSERT.
_ARRAY_TYPES = {
    "layer": "text[]",
    "ext": "text[]",
    "referrer": "text[]",
    "app": "text[]",
    "app_version": "text[]",
    "date": "timestamp[]",
    "x": "integer[]",
    "y": "integer[]",
    "z": "integer[]",
    "orig_z": "integer[]",
    "num_requests": "integer[]",
}


@dataclass
class TableImport:
    table: str
    source_rows: int
    source_requests: int
    before_rows: int
    after_rows: int
    after_requests: int

    @property
    def inserted(self) -> int:
        return self.after_rows - self.before_rows

    @property
    def reconciles(self) -> bool:
        """Whether the target's legacy lineage is exactly the source's."""
        return (self.after_rows, self.after_requests) == (
            self.source_rows,
            self.source_requests,
        )


def legacy_schema(source) -> str:
    """The schema holding the legacy tables in the source database.

    `stats` as the legacy tileserver left it; `tileserver_stats` where the
    retired `migrate-old` command renamed it in place.
    """
    found = [
        schema
        for (schema,) in source.run_query(
            """
            SELECT n.nspname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'day_index' AND c.relkind = 'r'
              AND n.nspname IN ('stats', 'tileserver_stats')
            """
        )
    ]
    if len(found) != 1:
        raise ValueError(
            "Expected one legacy day_index table in schema stats or "
            f"tileserver_stats; found {len(found)}."
        )
    schema = found[0]

    # A core Macrostrat database from before the consolidation migration also
    # has tileserver_stats.day_index, holding both lineages. Copying it would
    # file log-harvested rows as legacy ones.
    has_lineage_flag = source.run_query(
        """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.columns
          WHERE table_schema = :schema AND table_name = 'day_index'
            AND column_name = 'new_system'
        )
        """,
        {"schema": schema},
    ).scalar()
    if has_lineage_flag:
        raise ValueError(
            f"{schema}.day_index has a new_system column, so this is a core "
            "Macrostrat database, not the legacy tileserver_stats database. "
            "Use the usage-stats-consolidation migration there instead."
        )
    return schema


def _totals(db, relation: str, where: str = "") -> tuple[int, int]:
    count, total = db.run_query(
        f"SELECT count(*), coalesce(sum(num_requests), 0) FROM {relation} {where}"
    ).one()
    return int(count), int(total)


def import_legacy_lineage(source, target, *, batch_size: int = 10_000):
    """Copy the legacy day and location indexes from `source` into `target`.

    `source` is the environment's standalone `tileserver_stats` database and is
    only read. Returns a `TableImport` per table, comparing the target's legacy
    lineage after the import with the source.
    """
    schema = legacy_schema(source)
    results = []
    for source_table, (target_table, columns) in TABLES.items():
        relation = f"{schema}.{source_table}"
        destination = f"usage_stats.{target_table}"
        source_rows, source_requests = _totals(source, relation)
        before_rows, _ = _totals(target, destination, "WHERE NOT new_system")

        insert = (
            f"INSERT INTO {destination} ({', '.join(columns)}) "
            f"SELECT * FROM unnest("
            + ", ".join(f"CAST(:{c} AS {_ARRAY_TYPES[c]})" for c in columns)
            + f") ON CONFLICT ON CONSTRAINT {target_table}_unique DO NOTHING"
        )

        # Streamed, so the location index never sits in memory whole. Held, so
        # the cursor survives a commit on the source session between fetches.
        source.run_query(
            f"DECLARE legacy_rows NO SCROLL CURSOR WITH HOLD FOR "
            f"SELECT {', '.join(columns)} FROM {relation}"
        )
        try:
            while rows := source.run_query(
                f"FETCH {int(batch_size)} FROM legacy_rows"
            ).all():
                target.run_query(insert, dict(zip(columns, map(list, zip(*rows)))))
        finally:
            source.run_query("CLOSE legacy_rows")

        after_rows, after_requests = _totals(
            target, destination, "WHERE NOT new_system"
        )
        results.append(
            TableImport(
                table=destination,
                source_rows=source_rows,
                source_requests=source_requests,
                before_rows=before_rows,
                after_rows=after_rows,
                after_requests=after_requests,
            )
        )
    return results
