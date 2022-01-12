from fastapi import APIRouter
from fastapi.params import Depends
from urvogel.models import Environ
from ..depends import get_db
from urvogel.database.queries import get_sql
from psycopg.sql import SQL, Identifier

env_router = APIRouter(prefix="/environs")

""" functionality wanted
    Basic text match search by name
    Get by unit_id
"""
by_unit = get_sql("get_env_by_unit.sql")
simple_search = get_sql('basic-search.sql')

@env_router.get("/")
async def get_envs(unit_id: int = None, like: str =None, db=Depends(get_db)):
    sql = "SELECT * FROM macrostrat.environs;"
    if unit_id is not None:
        sql = SQL(by_unit).format(unit_id=unit_id)
    elif like is not None:
        like_ = like + "%"
        sql = SQL(simple_search).format(table=Identifier("macrostrat", "environs"),col=Identifier("environ"),like_=like_)

    res = db.query(sql).fetchall()
    envs = [Environ(**env) for env in res]
    return envs

