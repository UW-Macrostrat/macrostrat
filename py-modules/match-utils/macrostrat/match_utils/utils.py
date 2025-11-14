from pathlib import Path
from sqlalchemy.sql import text

_query_cache = {}


def stored_procedure(key: str):
    global _query_cache
    if key in _query_cache:
        return _query_cache[key]
    fn = Path(__file__).parent / "sql" / (key + ".sql")
    sql = text(fn.read_text())
    _query_cache[key] = sql
    return sql
