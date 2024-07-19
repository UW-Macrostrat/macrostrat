from pathlib import Path
import os
from psycopg import connect, rows

here = Path(__file__).parent

db_name = os.environ.get("POSTGRES_DB", "column_data")
db_port = os.environ.get("PG_PORT", "5434")
user = os.environ.get("PGUSER", "postgres")

class Database:
    def __init__(self, user: str = "postgres", password: str = None,autocommit: bool = True) -> None:
        
        if password is not None:
            user += f':{password}'

        conn_str = f"postgresql://{user}@localhost:{db_port}/{db_name}"

        self.conn = connect(conn_str, autocommit=autocommit, row_factory=rows.dict_row)
    
    def query(self, sql, params=None):
        return self.conn.cursor().execute(sql, params)

def get_sql(fn: str):
    fn = here / fn
    sql = open(fn).read()
    return sql