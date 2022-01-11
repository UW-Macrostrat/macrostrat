from fastapi import APIRouter, Depends
from .depends import get_db
from ..models import Column
from ..database.queries import get_sql, add_sql_clause
from psycopg.sql import SQL, Identifier

base_query = get_sql("get-cols-by.sql")

column_router = APIRouter(prefix="/columns")

## wanted functionality
## get by col_group_id
## by project

@column_router.get("/")
async def get_column(col_group_id: int = None, project_id: int = None, db = Depends(get_db)):
    sql = base_query
    params = None

    if col_group_id is not None:
        sql = add_sql_clause(sql, "WHERE {column} = {id}")
        sql = SQL(sql).format(column = Identifier('col_group_id'), id=col_group_id)
    elif project_id is not None:
        sql = add_sql_clause(sql, "WHERE {column} = {id}")
        sql = SQL(sql).format(column = Identifier('project_id'), id=project_id)
        
    res = db.query(sql, params).fetchall()
    cols = [Column(**col) for col in res]

    return cols

@column_router.get("/{col_id}")
async def get_col_id(col_id: int, db = Depends(get_db)):
    if col_id is not None:
            sql = add_sql_clause(base_query, f"WHERE id={col_id}")
            res = db.query(sql).fetchone()
            col = Column(**res)
            return col