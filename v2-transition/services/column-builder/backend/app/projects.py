from fastapi import APIRouter, Depends
from .depends import get_db
from ..database.queries import get_sql, add_sql_clause
from ..models import Project

project_router = APIRouter(prefix="/projects")
base_query = get_sql("get-projects.sql")

@project_router.get("/")
async def get_projects(all: bool = True, limit: int = 15,db = Depends(get_db)):
    if all:
        res = db.query(base_query).fetchall()
    else:
        res = db.query(base_query).fetchmany(limit)

    projects = [Project(**proj) for proj in res]
    return projects
    

@project_router.get("/{project_id}")
async def get_project_by_id(project_id: int = None, db = Depends(get_db)):
    if project_id is not None:
        sql = add_sql_clause(base_query, f"WHERE id={project_id}")
        res = db.query(sql).fetchone()
        project = Project(**res)
        return project
    
    
