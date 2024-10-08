from enum import Enum

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL, make_url


class ParameterStyle(Enum):
    MariaDB = "mariadb"
    MySQLDump = "mysqldump"


def build_connection_args(
    url: URL, style: ParameterStyle = ParameterStyle.MariaDB
) -> [str]:
    """Build MariaDB connection arguments from a SQLAlchemy URL."""

    args = [
        "-h",
        url.host,
        "-u",
        url.username,
    ]

    if url.port:
        args.extend(["-P" + str(url.port)])
    if url.password:
        args.extend(["-p" + str(url.password)])

    args.append(url.database)

    return args


def mariadb_engine(database: str = None):
    from macrostrat.core.config import mysql_database

    _database: URL = make_url(mysql_database)
    _database = _database.set(drivername="mysql+pymysql")
    if database is not None:
        _database = _database.set(database=database)
    return create_engine(_database)
