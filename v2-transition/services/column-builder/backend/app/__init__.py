from fastapi import FastAPI
from .projects import project_router
from .groups import groups_router
from .columns import column_router
from .units import units_router
from .defs import env_router, lith_router

app = FastAPI()
app.include_router(project_router)
app.include_router(groups_router)
app.include_router(column_router)
app.include_router(units_router)
app.include_router(env_router, prefix="/defs")
app.include_router(lith_router, prefix="/defs")

@app.get("/")
async def root():
    return {"Welcome": "Docs Future"}


""" 
HOW TO USE psycog for dynamic inserts
https://www.psycopg.org/psycopg3/docs/api/sql.html#module-psycopg.sql
===============================================

name = ['foo', 'bar', 'baz']
q2 = sql.SQL("INSERT INTO my_table ({}) VALUES ({})").format(
    sql.SQL(', ').join(map(sql.Identifier, names)),
    sql.SQL(', ').join(map(sql.Placeholder, names)))

print(q2.as_string(conn))
    INSERT INTO my_table ("foo", "bar", "baz") VALUES (%(foo)s, %(bar)s, %(baz)s)

"""