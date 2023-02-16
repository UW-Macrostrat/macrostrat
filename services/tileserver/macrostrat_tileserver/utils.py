from pathlib import Path

stmt_cache = {}

def prepared_statement(id):
    cached = stmt_cache.get(id)
    if cached is None:
        stmt_cache[id] = (Path(__file__).parent / "sql" / f"{id}.sql").open("r").read()
    return stmt_cache[id]
