"""Command-time environment for the local docker-compose stack.

The compose file interpolates ``POSTGRES_*``, ``SECRET_KEY``, ``STORAGE_*`` and
``ELEVATION_DATABASE_URL`` from the process environment, and the database
container initialises its password from ``POSTGRES_PASSWORD``. Those values
have to be plaintext when ``docker compose`` runs. A literal config exports
them at import; a vaulted one deliberately does not (see
:func:`~macrostrat.core.config._ambient_database_url`), so they are resolved
here — once, for the one invocation that is about to start the stack, and only
for the variables not already present.

This is the smallest thing that works. Compose is local by nature, so it gets
no injection architecture: ``os.environ`` is set and ``docker compose``
inherits it, exactly as it always has.
"""

from os import environ
from typing import Callable, Dict, Optional

from macrostrat.utils import get_logger

from .connections import DEFAULT_DATABASE, DatabaseRole, MissingCredential
from .secrets import SecretResolutionError

log = get_logger(__name__)

#: Top-level commands that run `docker compose` and so read these variables.
COMPOSE_COMMANDS = frozenset({"up", "restart", "compose"})

#: The default database's variables. If *any* is missing, all are exported.
DATABASE_VARIABLES = (
    "PGHOST",
    "PGPORT",
    "PGUSER",
    "PGPASSWORD",
    "PGDATABASE",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "MACROSTRAT_DB_PORT",
    "MACROSTRAT_DATABASE_URL",
)


def export_compose_environment(settings, env: Optional[Dict[str, str]] = None):
    """Resolve and export what the compose stack reads, where not already set.

    *env* defaults to :data:`os.environ`; tests pass a dict. Each source is
    tried independently, so one unresolvable reference (the wrong 1Password
    account, say) costs the stack that variable and a warning, not the whole
    start. Values are never logged.
    """
    if env is None:
        env = environ
    exported = []

    def attempt(label: str, populate: Callable[[], bool]):
        """Run one source; count it only if it actually set something."""
        try:
            did = populate()
        except (SecretResolutionError, MissingCredential) as err:
            log.warning("Not exporting %s for the compose stack: %s", label, err)
        except Exception as err:  # a missing endpoint, an unset key
            log.debug("Not exporting %s for the compose stack: %s", label, err)
        else:
            if did:
                exported.append(label)

    from .config import export_database_environment, exported_database_url

    if not all(name in env for name in DATABASE_VARIABLES):

        def database():
            conn = settings.database_connection(DEFAULT_DATABASE)
            if conn is None:
                return False
            url = exported_database_url(conn, DatabaseRole.Writer)
            export_database_environment(url, env)
            return True

        attempt("the database login", database)

    if "ELEVATION_DATABASE_URL" not in env:

        def elevation():
            conn = settings.database_connection("elevation")
            if conn is None:
                return False
            env["ELEVATION_DATABASE_URL"] = exported_database_url(
                conn, DatabaseRole.Writer
            )
            return True

        attempt("ELEVATION_DATABASE_URL", elevation)

    if "SECRET_KEY" not in env:

        def signing_key():
            key = settings.resolve_token_signing_key()
            if key is None:
                return False
            env["SECRET_KEY"] = key
            return True

        attempt("SECRET_KEY", signing_key)

    if "STORAGE_ACCESS_KEY" not in env or "STORAGE_SECRET_KEY" not in env:

        def storage():
            endpoint = settings.storage_endpoint()
            if endpoint is None:
                return False
            access, secret = endpoint.credentials()
            env["STORAGE_ACCESS_KEY"] = access
            env["STORAGE_SECRET_KEY"] = secret
            return True

        attempt("STORAGE_*", storage)

    if exported:
        log.info(
            "Resolved for the compose stack (this invocation only): %s",
            ", ".join(exported),
        )
    return exported
