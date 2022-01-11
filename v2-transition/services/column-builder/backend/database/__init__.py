from psycopg import connect, rows
from ..config import pg_url

class Database:
    def __init__(self, conn_str: str = pg_url, autocommit: bool = True) -> None:
        self.conn = connect(conn_str, autocommit=autocommit, row_factory=rows.dict_row)

    def execute_transaction(self,sql):
        """ 
        Handle transaction contexts
        https://www.psycopg.org/psycopg3/docs/basic/transactions.html#transactions
        
        """
        with self.conn.cursor() as cur:
            with self.conn.transaction():
                # will autocommit or rollback if exception is triggered
                cur.execute(sql)
    
    def query(self, sql, params=None):
        return self.conn.cursor().execute(sql, params)
        

