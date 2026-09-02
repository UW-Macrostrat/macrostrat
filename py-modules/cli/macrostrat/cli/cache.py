"""
Tile cache management CLI
"""

from typer import Option, Typer, confirm

from macrostrat.core.database import get_database

cli = Typer(name="cache", help="Tile cache management")


@cli.command(name="clear")
def clear_cache(
    yes: bool = Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
):
    """Clear the tile cache.

    Uses TRUNCATE rather than DELETE. DELETE leaves the space allocated to the
    relation for autovacuum to reclaim later and writes WAL in proportion to the
    rows removed -- on a volume that is already full it frees nothing while making
    the immediate problem worse, which is how the September 2026 outage deepened.
    TRUNCATE returns the space immediately and writes almost no WAL.

    The cost is a brief ACCESS EXCLUSIVE lock: in-flight tile requests block until
    it completes, and the cache repopulates on demand afterwards.
    """
    db = get_database()

    tiles, size = db.run_query(
        """SELECT
            greatest(
                (SELECT reltuples FROM pg_class
                 WHERE oid = 'tile_cache.tile'::regclass),
                0
            )::bigint AS tiles,
            pg_size_pretty(pg_total_relation_size('tile_cache.tile')) AS size"""
    ).one()

    if not yes:
        confirm(
            f"Truncate tile_cache.tile (about {tiles:,} tiles, {size})? "
            "Tile requests will block briefly and the cache will be cold.",
            abort=True,
        )

    db.run_query("TRUNCATE tile_cache.tile")
    db.session.commit()

    print(f"Truncated tile_cache.tile — reclaimed {size} (about {tiles:,} tiles)")
