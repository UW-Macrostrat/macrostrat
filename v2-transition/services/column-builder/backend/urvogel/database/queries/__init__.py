from pathlib import Path
from psycopg.sql import SQL, Identifier

here = Path(__file__).parent

def get_sql(fn: str):
    fn = here / fn
    sql = open(fn).read()
    return sql

def add_sql_clause(sql:str, add:str):
    if sql[-1] == ";" or sql[-1] == " ":
        return sql[:-1] + " " +  add + ";"

def add_where_clause(sql: str, col:str, value:str|int):
    """ Dynamically create a where clause """
    primary = add_sql_clause(sql, 'WHERE {col} = {val}')
    where = SQL(primary).format(col=Identifier(col), val=value)
    return where
    