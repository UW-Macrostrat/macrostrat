from fastapi import FastAPI
from .projects import project_router
from .groups import groups_router
from .columns import column_router

app = FastAPI()
app.include_router(project_router)
app.include_router(groups_router)
app.include_router(column_router)

@app.get("/")
async def root():
    return {"Welcome": "Docs Future"}

