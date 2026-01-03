# Via the ad-hoc migrations in these two repositories
# https://github.com/UW-Macrostrat/postgis-tile-utils @ 1ef18f99436eff1d833b6b0463946644f249763a
# https://github.com/UW-Macrostrat/tileserver @ v2.1.0

from pathlib import Path

from macrostrat.core.migrations import Migration

__dir__ = Path(__file__).parent


class TileLayersMigration(Migration):
    name = "macrostrat-tile-layers"
    subsystem = "tileserver"
    description = """
    Create tileserver views
    """
    readiness_state = "ga"

    always_apply = True
    depends_on = ["macrostrat-tileserver"]
