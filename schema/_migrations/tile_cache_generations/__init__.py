"""The tile cache as a ring of unlogged generations beside a logged pinned partition."""

from pathlib import Path

from macrostrat.database import Database
from macrostrat.schema_management import ApplicationStatus, Migration

_core = Path(__file__).parents[2] / "core"


def _relkind(db: Database) -> str | None:
    """`p` once partitioned, `r` for the old table, None when absent."""
    return db.run_query(
        "SELECT relkind FROM pg_class WHERE oid = to_regclass('tile_cache.tile')"
    ).scalar()


def _drop_old_cache(db: Database):
    # A plain table cannot become a partitioned one; the cache refills on demand.
    db.run_sql("DROP TABLE tile_cache.tile CASCADE", raise_errors=True)


class TileCacheGenerationsMigration(Migration):
    name = "tile-cache-generations"
    subsystem = "core"
    description = """
    Rebuild `tile_cache.tile` as a generational cache: six unlogged generations
    evicted by `TRUNCATE`, and a logged partition for pinned tiles. Every cached
    tile is dropped and the cache refills on demand. Deploy the tileservers that
    read the new layout first; older ones fail their cache lookups against it.
    """
    depends_on = []
    readiness_state = "alpha"
    destructive = True

    fixtures = [
        _drop_old_cache,
        _core / "0032-tile_cache.sql",
        _core / "0033-tile_cache.sources.sql",
    ]

    def should_apply(self, db: Database) -> ApplicationStatus:
        kind = _relkind(db)
        if kind == "p":
            return ApplicationStatus.APPLIED
        if kind == "r":
            return ApplicationStatus.CAN_APPLY
        return ApplicationStatus.CANT_APPLY
