from macrostrat.utils.shell import run
from .._legacy import get_db

from macrostrat.core import app

from ..._dev.utils import (
    _create_database_if_not_exists,
    _docker_local_run_args,
)


def import_mariadb(target_database="macrostrat_from_mariadb"):
    """Import legacy MariaDB database to PostgreSQL using pgloader"""
    # Run pgloader in docker

    cfg = app.settings

    args = _docker_local_run_args(postgres_container="dimitri/pgloader")

    # Get the database URL
    db = get_db()
    url = db.engine.url
    url = url.set(database=target_database)

    _create_database_if_not_exists(url, create=True)

    pg_url = str(url)

    dburl = cfg.get("mysql_database", None)
    if dburl is None:
        raise Exception("No MariaDB database URL available in configuration")

    run(
        *args,
        "pgloader",
        "--with",
        "prefetch rows = 1000",
        str(dburl),
        str(pg_url),
    )
