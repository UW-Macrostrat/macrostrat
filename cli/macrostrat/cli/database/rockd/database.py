from macrostrat.database import Database
import os

def get_rockd_db() -> Database:
    """
    Return a Database instance that talks to the Rockd cluster.
    The URL can live in .env / docker-compose.yml as ROCKD_DATABASE.
    """
    url = os.environ.get("ROCKD_DATABASE")
    if url is None:
        raise RuntimeError("Set ROCKD_DATABASE in your environment")
    return Database(url)
get_db = get_rockd_db
