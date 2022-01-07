from pathlib import Path

here = Path(__file__).parent

def get_sql(fn: str):
    fn = here / fn
    sql = open(fn).read()
    return sql