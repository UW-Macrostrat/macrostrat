from os import environ
from dynaconf import Dynaconf

from .utils import find_macrostrat_config

macrostrat_env = environ.get("MACROSTRAT_ENV", None)

cfg = find_macrostrat_config()

settings = Dynaconf(
    envvar_prefix="MACROSTRAT",
    environments=True,
    env=macrostrat_env,
    settings_files=[cfg],
    load_dotenv=False,
)

# A database connection string for PostgreSQL
PG_DATABASE = settings.pg_database
#environ.get("MACROSTRAT_PG_DATABASE", None)

# A database connection string for MySQL
# This should eventually become optional if it isn't already
MYSQL_DATABASE = settings.mysql_database
#environ.get("MACROSTRAT_MYSQL_DATABASE", None)


# REDIS_PORT = environ.get("REDIS_PORT", None)

# Tile caching
#CACHE_PATH = environ.get("TILE_CACHE_PATH", "./tiles/burwell")
#CACHE_PATH_VECTOR = environ.get("TILE_CACHE_PATH_VECTOR", CACHE_PATH)

#TILESERVER_SECRET = environ.get("TILESERVER_SECRET", None)
#MBTILES_PATH = environ.get("MBTILES_PATH", None)
