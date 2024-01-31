from os import environ
from pathlib import Path

from dynaconf import Dynaconf, Validator
from sqlalchemy.engine import make_url

from .utils import find_macrostrat_config, is_pg_url

cfg = find_macrostrat_config()

macrostrat_config_file = cfg

settings = Dynaconf(
    envvar_prefix="MACROSTRAT",
    environments=True,
    env_switcher="MACROSTRAT_ENV",
    settings_files=[cfg],
    load_dotenv=False,
)

settings.validators.register(
    # `must_exist` is causing huge problems
    # Validator("COMPOSE_ROOT", "CORELLE_SRC", must_exist=False, cast=Path),
    Validator("COMPOSE_ROOT", "CORELLE_SRC", cast=Path)
)

macrostrat_env = settings.env

settings.validators.validate()

# A database connection string for PostgreSQL
PG_DATABASE = settings.pg_database
# environ.get("MACROSTRAT_PG_DATABASE", None)
# On mac and windows, we need to use the docker host `host.docker.internal` or `host.lima.internal`, etc.
docker_localhost = getattr(settings, "docker_localhost", "localhost")
PG_DATABASE_DOCKER = PG_DATABASE.replace("localhost", docker_localhost)


# Set environment variables
url = make_url(PG_DATABASE)

environ["PGPASSWORD"] = url.password
environ["PGHOST"] = url.host
environ["PGPORT"] = str(url.port)
environ["PGUSER"] = url.username
environ["PGDATABASE"] = url.database

environ["PG_DATABASE_CONTAINER"] = getattr(
    settings, "pg_database_container", "postgis/postgis:15-3.4"
)


environ["COMPOSE_PROJECT_NAME"] = "macrostrat_" + macrostrat_env

# For map integration CLI
if getattr(settings, "ingestion_database", None) is None:
    settings.ingestion_database = PG_DATABASE

if not is_pg_url(settings.ingestion_database):
    # Set the ingestion database to the same cluster as the main database
    settings.ingestion_database = str(url.set(database=settings.ingestion_database))


environ["INTEGRATION_DATABASE_URL"] = settings.ingestion_database
environ["MACROSTRAT_DATABASE_URL"] = PG_DATABASE

# Docker compose file
compose_file = getattr(settings, "compose_file", None)
if compose_file is None:
    root = getattr(settings, "compose_root", None)
    if root is not None:
        compose_root = Path(root).expanduser()
        environ["COMPOSE_ROOT"] = str(compose_root)
        compose_file = compose_root / "docker-compose.yaml"
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

# Path to the root of the Macrostrat repository
settings.srcroot = Path(__file__).parent.parent.parent.parent

environ["MACROSTRAT_ROOT"] = str(settings.srcroot)
