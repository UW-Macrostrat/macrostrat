from fastapi import APIRouter, Depends
from .depends import get_db
from ..database.queries import get_sql, add_sql_clause
from ..models import ColumnGroup

groups_router = APIRouter(prefix="/groups")
base_query = get_sql("get-groups.sql")


@groups_router.get("/")
async def get_columns(project_id: int = None, all: bool = False, limit: int=15, db = Depends(get_db)):
    
    sql = base_query
    params = None

    if project_id is not None:
        sql = get_sql("get-groups-by-project.sql")
        params = {"project_id":project_id}
    if all:
        res = db.query(sql, params).fetchall()
    else:
        res = db.query(sql, params).fetchmany(limit)

    groups = [ColumnGroup(**group) for group in res]
    return groups

@groups_router.get("/{group_id}")
async def get_project_by_id(group_id: int = None, db = Depends(get_db)):
    if group_id is not None:
        sql = add_sql_clause(base_query, f"WHERE id={group_id}")
        res = db.query(sql).fetchone()
        group = ColumnGroup(**res)
        return group

