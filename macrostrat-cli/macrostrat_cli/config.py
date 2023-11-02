from os import environ
from dynaconf import Dynaconf, Validator
from pathlib import Path

from .utils import find_macrostrat_config
from sqlalchemy.engine import make_url


cfg = find_macrostrat_config()

settings = Dynaconf(
    envvar_prefix="MACROSTRAT",
    environments=True,
    settings_files=[cfg],
    load_dotenv=False,
    validators=[
        Validator("COMPOSE_ROOT", "CORELLE_SRC", must_exist=False, cast=Path),
    ],
)

macrostrat_env = environ.get("MACROSTRAT_ENV", "local")
settings.namespace(macrostrat_env)

# A database connection string for PostgreSQL
PG_DATABASE = settings.pg_database
# environ.get("MACROSTRAT_PG_DATABASE", None)


# Set environment variables
url = make_url(PG_DATABASE)

environ["PGPASSWORD"] = url.password
environ["PGHOST"] = url.host
environ["PGPORT"] = str(url.port)
environ["PGUSER"] = url.username
environ["PGDATABASE"] = url.database

environ["COMPOSE_PROJECT_NAME"] = "macrostrat_" + macrostrat_env

# Docker compose file
compose_file = getattr(settings, "compose_file", None)
if compose_file is None:
    root = getattr(settings, "compose_root", None)
    if root is not None:
        compose_file = Path(settings.compose_root).expanduser() / "docker-compose.yaml"
if compose_file is not None:
    environ["COMPOSE_FILE"] = str(compose_file)

settings.project_name = environ["COMPOSE_PROJECT_NAME"]

# A database connection string for MySQL
# This should eventually become optional if it isn't already
MYSQL_DATABASE = getattr(settings, "mysql_database", None)


# environ.get("MACROSTRAT_MYSQL_DATABASE", None)


# REDIS_PORT = environ.get("REDIS_PORT", None)

# Tile caching
# CACHE_PATH = environ.get("TILE_CACHE_PATH", "./tiles/burwell")
# CACHE_PATH_VECTOR = environ.get("TILE_CACHE_PATH_VECTOR", CACHE_PATH)

# TILESERVER_SECRET = environ.get("TILESERVER_SECRET", None)
# MBTILES_PATH = environ.get("MBTILES_PATH", None)
