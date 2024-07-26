from sqlalchemy.engine.url import URL


def build_connection_args(url: URL) -> [str]:
    """Build MariaDB connection arguments from a SQLAlchemy URL."""
    args = [
        "-h",
        url.host,
        "-P",
        str(url.port),
        "-u",
        url.username,
        "-D",
        url.database,
    ]
    if url.password:
        args.extend(["-p" + str(url.password)])
    return args
