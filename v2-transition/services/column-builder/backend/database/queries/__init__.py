from pathlib import Path

here = Path(__file__).parent

def get_sql(fn: str):
    fn = here / fn
    sql = open(fn).read()
    return sql

def add_sql_clause(sql:str, add:str):
    if sql[-1] == ";" or sql[-1] == " ":
        return sql[:-1] + " " +  add + ";"
