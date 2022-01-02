from os import environ

# A database connection string for PostgreSQL
PG_DATABASE = environ.get("MACROSTRAT_PG_DATABASE", None)

# A database connection string for MySQL
# This should eventually become optional if it isn't already
MYSQL_DATABASE = environ.get("MACROSTRAT_MYSQL_DATABASE", None)

REDIS_PORT = environ.get("REDIS_PORT", None)

# Tile caching
CACHE_PATH = environ.get("TILE_CACHE_PATH", "./tiles/burwell")
CACHE_PATH_VECTOR = environ.get("TILE_CACHE_PATH_VECTOR", CACHE_PATH)

TILESERVER_SECRET = environ.get("TILESERVER_SECRET", None)
MBTILES_PATH = environ.get("MBTILES_PATH", None)
