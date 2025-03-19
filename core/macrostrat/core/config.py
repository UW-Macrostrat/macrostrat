from os import environ
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from dynaconf import Dynaconf, Validator
from pydantic import BaseModel
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL
from toml import load as load_toml

from macrostrat.app_frame.control_command import BackendType
from macrostrat.utils import get_logger

from .utils import find_macrostrat_config

log = get_logger(__name__)


class MacrostratConfig(Dynaconf):
    """Macrostrat config manager that reads from a TOML file"""

    config_file: Path

    def __init__(self, *args, **kwargs):
        cfg = find_macrostrat_config()
        settings = []
        if cfg is not None:
            settings.append(cfg)

        super().__init__(
            envvar_prefix="MACROSTRAT",
            environments=True,
            env_switcher="MACROSTRAT_ENV",
            settings_files=settings,
            # We load dotenv files on our own
            load_dotenv=False,
        )

        self.config_file = None
        if cfg is not None:
            self.config_file = Path(cfg)

    def all_environments(self):
        # Parse out top-level headers from TOML file
        with open(self.config_file, "r") as f:
            cfg = load_toml(f)
            keys = iter(cfg.keys())
            next(keys)
            return [k for k in keys]

    def get(self, key, default=None):
        if not "." in key:
            return getattr(self, key, default)

        keys = key.split(".")
        for k in keys:
            if k not in self:
                return default
            self = getattr(self, k)
        return self


settings = MacrostratConfig()


def convert_to_string(value):
    if value is None:
        return None
    return str(value)


settings.validators.register(
    # `must_exist` is causing huge problems
    Validator("COMPOSE_ROOT", cast=Path),
    Validator("env_files", cast=list[Path]),
    Validator("pg_database", cast=convert_to_string, default=None),
    # Backend information. We could potentially infer this from other environment variables
    Validator("backend", default="kubernetes", cast=BackendType),
)

macrostrat_env = getattr(settings, "env", "default")

if env_files := getattr(settings, "env_files", None):
    for env in env_files:
        e = Path(env)
        if not e.is_absolute():
            # Resolve relative to config file
            e = settings.config_file.parent / e

        if not e.exists():
            raise FileNotFoundError(f"Environment file {e} not found")

        log.info(f"Loading environment variables from {e}")
        load_dotenv(e)


settings.validators.validate()

# Settings for storage, if provided
if storage := getattr(settings, "storage", None):
    access_key = storage.get("access_key", None)
    secret_key = storage.get("secret_key", None)
    if access_key is None or secret_key is None:
        raise ValueError("Access key and secret key must be provided for storage")

    environ["STORAGE_ACCESS_KEY"] = access_key
    environ["STORAGE_SECRET_KEY"] = secret_key

# A database connection string for PostgreSQL
PG_DATABASE = getattr(settings, "pg_database", None)
url = None
# Not sure why this happens
if PG_DATABASE == "None":
    PG_DATABASE = None
# environ.get("MACROSTRAT_PG_DATABASE", None)
if PG_DATABASE is not None:
    # On mac and windows, we need to use the docker host `host.docker.internal` or `host.lima.internal`, etc.
    docker_localhost = getattr(settings, "docker_localhost", "localhost")
    PG_DATABASE_DOCKER = PG_DATABASE.replace("localhost", docker_localhost)

    # Set environment variables
    url = make_url(PG_DATABASE)

    environ["PGHOST"] = url.host
    environ["PGPORT"] = str(url.port)

    for v in ("PGPASSWORD", "POSTGRES_PASSWORD"):
        environ[v] = url.password

    for v in ("PGUSER", "POSTGRES_USER"):
        environ[v] = url.username

    for v in ("PGDATABASE", "POSTGRES_DB"):
        environ[v] = url.database

    # Used for local running of Macrostrat
    environ["MACROSTRAT_DB_PORT"] = str(url.port)

    environ["MACROSTRAT_DATABASE_URL"] = PG_DATABASE

mysql_database = getattr(settings, "mysql_database", None)
if mysql_database is not None:
    mysql_database: URL = make_url(mysql_database).set(drivername="mysql+pymysql")
    # TODO: handle this more intelligently


if elevation_database := getattr(settings, "elevation_database", None):
    environ["ELEVATION_DATABASE_URL"] = elevation_database


environ["PG_DATABASE_CONTAINER"] = getattr(
    settings, "pg_database_container", "postgis/postgis:15-3.4"
)

# Set defaults
# Ideally we should be able to do this in the settings object
settings.offline = getattr(settings, "offline", False)


environ["COMPOSE_PROJECT_NAME"] = "macrostrat_" + macrostrat_env

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

if mapbox_token := getattr(settings, "mapbox_token", None):
    environ["MAPBOX_TOKEN"] = mapbox_token

if secret_key := getattr(settings, "secret_key", None):
    environ["SECRET_KEY"] = secret_key

# Path to the root of the Macrostrat repository
settings.srcroot = Path(__file__).parent.parent.parent.parent

environ["MACROSTRAT_ROOT"] = str(settings.srcroot)


# Setup source roots for application components
class Sources(BaseModel):
    api: Optional[Path] = None
    api_v3: Optional[Path] = None
    tileserver: Optional[Path] = None
    corelle: Optional[Path] = None
    web: Optional[Path] = None
    map_cache: Optional[Path] = None


def get_source(key: str) -> Optional[Path]:
    sources = getattr(settings, "sources", None)
    if sources is None:
        return None
    src = getattr(sources, key, None)
    if src is not None:
        return Path(src)
    return None


def setup_environment(sources: Sources):
    for k, v in sources.dict().items():
        if v is not None:
            environ[f"MACROSTRAT_{k.upper()}_SRC"] = str(v)


settings.sources = Sources(
    api=get_source("api"),
    api_v3=get_source("api_v3"),
    tileserver=get_source("tileserver"),
    corelle=get_source("corelle"),
    web=get_source("web"),
    map_cache=get_source("map_cache"),
)

setup_environment(settings.sources)

# Settings for local installation
