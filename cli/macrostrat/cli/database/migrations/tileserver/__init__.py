# Via the ad-hoc migrations in these two repositories
# https://github.com/UW-Macrostrat/postgis-tile-utils @ 1ef18f99436eff1d833b6b0463946644f249763a
# https://github.com/UW-Macrostrat/tileserver @ v2.1.0

from pathlib import Path

from macrostrat.core.migrations import Migration, schema_exists

__dir__ = Path(__file__).parent


class TileserverMigration(Migration):
    name = "macrostrat-tileserver"
    subsystem = "tileserver"
    description = """
    Populate the `tile_cache` and `tile_utils` schemas
    """
    depends_on = ["macrostrat-mariadb", "maps-lines-oriented"]

    postconditions = [schema_exists("tile_cache"), schema_exists("tile_utils")]
