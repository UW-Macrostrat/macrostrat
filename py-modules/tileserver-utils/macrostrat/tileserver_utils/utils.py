from contextvars import ContextVar
from pathlib import Path

_query_index = ContextVar("query_index", default={})


def _update_query_index(key, value):
    _query_index.set({**_query_index.get(), key: value})


def get_sql(filename: Path):
    ix = _query_index.get()
    if filename in ix:
        return ix[filename]

    q = filename.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]
    _update_query_index(filename, q)
    return q


def prepared_statement(id):
    """Legacy prepared statement"""
    filename = Path(__file__).parent / "sql" / f"{id}.sql"
    return get_sql(filename)
