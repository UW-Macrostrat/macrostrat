from fastapi import APIRouter
from fastapi.params import Depends
from psycopg.sql import SQL
from .depends import get_db
from ..database.queries import get_sql, add_sql_clause
from ..models import Unit

units_router = APIRouter(prefix="/units")
base_query = get_sql("get-units-by.sql")

""" functionality wanted:

filter by: project_id, column_group, column_id, section_id 

"""

join_cols = """LEFT JOIN macrostrat.cols c ON c.id = u.col_id"""

project = join_cols + " WHERE c.project_id={id}"
col_group = join_cols + " WHERE c.col_group_id={id}"

@units_router.get("/")
async def get_units(
    project_id: int = None,
    col_group_id: int = None, 
    col_id : int= None, 
    section_id: int = None, 
    db = Depends(get_db)
    ):
    sql = base_query

    if project_id is not None:
        sql = add_sql_clause(sql, project)
        sql = SQL(sql).format(id=project_id)
    elif col_group_id is not None:
        sql = SQL(add_sql_clause(sql, col_group)).format(id=col_group_id)
    elif col_id is not None:
        sql = SQL(add_sql_clause(sql, "WHERE u.col_id={id}")).format(id=col_id)
    elif section_id is not None:
        sql = SQL(add_sql_clause(sql, "WHERE u.section_id={id}")).format(id=section_id)

    res = db.query(sql).fetchall()
    units = [Unit(**unit) for unit in res]
    return units

@units_router.get("/{unit_id}")
async def get_unit_by_id(unit_id: int, db = Depends(get_db)):
    sql = add_sql_clause(base_query, f"WHERE id={unit_id}")
    res = db.query(sql).fetchone()
    unit = Unit(**res)
    return unit
