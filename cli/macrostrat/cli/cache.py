"""
Tile cache management CLI
"""

from typer import Typer

from macrostrat.core.database import get_database

cli = Typer(name="cache", help="Tile cache management")


@cli.command(name="clear")
def clear_cache():
    """Clear the tile cache"""

    condition = "true"

    sql = f"""WITH delete AS (
        DELETE FROM tile_cache.tile WHERE {condition} RETURNING x, y, z
    ) SELECT count(*) FROM delete"""
    db = get_database()
    count = db.run_query(sql).scalar()
    db.session.commit()
    print(f"Deleted {count} cached tiles")
