from fastapi import APIRouter
from fastapi.params import Depends
from urvogel.models import Lith
from urvogel.database.queries import get_sql
from ..depends import get_db
from psycopg.sql import SQL, Identifier

lith_router = APIRouter(prefix="/liths")

""" functionality wanted
    Basic text match search by name
    Get by unit_id
"""

by_unit = get_sql("get_lith_by_unit.sql")
simple_search = get_sql('basic-search.sql')

@lith_router.get("/")
async def get_lith(unit_id: int = None, like: str = None, db= Depends(get_db)):
    sql = "SELECT * FROM macrostrat.liths"

    if unit_id is not None:
        sql = SQL(by_unit).format(unit_id=unit_id)
    elif like is not None:
        like_ = like + "%"
        sql = SQL(simple_search).format(table=Identifier("macrostrat", "liths"),col=Identifier("lith"),like_=like_)
    
    res = db.query(sql).fetchall()
    liths = [Lith(**lith) for lith in res]

    return liths