from contextvars import ContextVar

from sqlalchemy import create_engine

from macrostrat.database import Database

from ..config import PG_DATABASE

db_ctx: ContextVar[Database | None] = ContextVar("db_ctx", default=None)


def get_database():
    from macrostrat.database import Database

    db = db_ctx.get()
    if db is None:
        db = Database(PG_DATABASE)
        db_ctx.set(db)
    return db


def refresh_database():
    db = get_database()
    db.session.flush()
    db.session.close()
    db_ctx.set(None)
    return get_database()


def engine_for_db_name(name: str | None):
    engine = get_database().engine
    if name is None:
        return engine
    url = engine.url.set(database=name)
    return create_engine(url)
