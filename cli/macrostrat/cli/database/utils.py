from ._legacy import get_db
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL, make_url
from macrostrat.core.config import settings


def engine_for_db_name(name: str | None):
    engine = get_db().engine
    if name is None:
        return engine
    url = engine.url.set(database=name)
    return create_engine(url)


def docker_internal_url(url: URL | str) -> URL:
    url = make_url(url)
    if url.host == "localhost":
        docker_localhost = getattr(settings, "docker_localhost", "localhost")
        url = url.set(host=docker_localhost)
    return url
