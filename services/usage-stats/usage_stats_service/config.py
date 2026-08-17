"""Environment configuration for the usage-stats worker.

The library (`macrostrat.usage_stats_capture`) holds no configuration; this is
the service's half of that split. Everything comes from environment variables,
so the container needs nothing else — no config file, no Macrostrat settings
machinery.

    USAGE_STATS_DATABASE_URL    PostgreSQL URL. Falls back to
                                MACROSTRAT_DATABASE_URL, then DATABASE_URL.
    USAGE_STATS_S3_ENDPOINT     Object storage holding the access logs.
    USAGE_STATS_S3_BUCKET
    USAGE_STATS_S3_ACCESS_KEY
    USAGE_STATS_S3_SECRET_KEY
    USAGE_STATS_CLIENT_SALT     Secret used to pseudonymize client addresses.
"""

from os import environ

from macrostrat.usage_stats_capture import S3Params


class ConfigError(RuntimeError):
    """Raised when required configuration is missing, naming what to set."""


def database_url() -> str:
    for var in ("USAGE_STATS_DATABASE_URL", "MACROSTRAT_DATABASE_URL", "DATABASE_URL"):
        value = environ.get(var)
        if value:
            return value
    raise ConfigError(
        "No database configured. Set USAGE_STATS_DATABASE_URL "
        "(or MACROSTRAT_DATABASE_URL / DATABASE_URL)."
    )


def get_db():
    from macrostrat.database import Database

    return Database(database_url())


def storage() -> S3Params:
    fields = {}
    missing = []
    for field, var in (
        ("bucket", "USAGE_STATS_S3_BUCKET"),
        ("endpoint", "USAGE_STATS_S3_ENDPOINT"),
        ("access_key", "USAGE_STATS_S3_ACCESS_KEY"),
        ("secret_key", "USAGE_STATS_S3_SECRET_KEY"),
    ):
        value = environ.get(var)
        if not value:
            missing.append(var)
        fields[field] = value

    if missing:
        raise ConfigError(
            "Object storage is not configured; missing " + ", ".join(missing) + "."
        )
    return S3Params(**fields)


def client_salt() -> bytes:
    """Secret used to pseudonymize client addresses.

    Must be secret and stable: a bare digest of an IPv4 address inverts by brute
    force in seconds, and changing the salt forks `client_id`, silently breaking
    deduplication against everything already ingested. Treat it with the same
    care as a database credential.
    """
    value = environ.get("USAGE_STATS_CLIENT_SALT")
    if not value:
        raise ConfigError(
            "Cannot pseudonymize client addresses: set USAGE_STATS_CLIENT_SALT. "
            "Changing this value later forks client_id and breaks deduplication "
            "against already-ingested rows."
        )
    return value.encode()
