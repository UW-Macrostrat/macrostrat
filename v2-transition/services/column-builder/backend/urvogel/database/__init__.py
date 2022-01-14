from psycopg import connect, rows
from psycopg.sql import SQL, Identifier, Literal
from pydantic.main import BaseModel
from ..config import pg_url

class Database:
    def __init__(self, conn_str: str = pg_url, autocommit: bool = True) -> None:
        self.conn = connect(conn_str, autocommit=autocommit, row_factory=rows.dict_row)
    
    def query(self, sql, params=None):
        return self.conn.cursor().execute(sql, params)
    
    def insert(self, model:BaseModel, table: str , schema: str=None) -> int:
        sql = """INSERT INTO {table} ({columns})
                    VALUES ({values}) RETURNING id"""
        
        fields, values = zip(*[(k,v) for k,v in model if v is not None])

        fields = SQL(',').join([Identifier(field) for field in fields])
        values= SQL(",").join([Literal(v) for v in values])

        sql = SQL(sql).format(table=Identifier(schema,table), columns = fields, values=values)

        with self.conn.cursor() as cur:
            with self.conn.transaction():
                res = cur.execute(sql).fetchone()

        return res.get('id')

    def update(self, model:BaseModel, table:str,schema:str = None) ->int:
        sql = """UPDATE {table} SET {setters} WHERE id={id} RETURNING id"""

        setters = [SQL('{column}={value}').format(column = Identifier(k), value=Literal(v)) for k,v in model if v is not None]
        
        table = Identifier(schema, table)

        sql = SQL(sql).format(table=table, setters = SQL(",").join(setters), id=model.id)

        with self.conn.cursor() as cur:
            with self.conn.transaction():
                res = cur.execute(sql).fetchone()
        
        return res.get('id')