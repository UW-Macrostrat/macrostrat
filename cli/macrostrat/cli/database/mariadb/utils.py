from sqlalchemy.engine.url import URL
from enum import Enum


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
        "-P",
        str(url.port),
        "-u",
        url.username,
    ]
    if url.password:
        args.extend(["-p" + str(url.password)])

    if style == ParameterStyle.MariaDB:
        args.extend(["-D", url.database])
    elif style == ParameterStyle.MySQLDump:
        args.extend(["--databases", url.database])

    return args
