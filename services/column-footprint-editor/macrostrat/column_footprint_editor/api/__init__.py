from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

from ..settings import DATABASE
from .column_groups import ColumnGroups
from .geometries import Lines, Points, geometries, get_csv, get_line, import_topologies
from .home import HomePage
from .project import ProjectsAPI
from .voronoi import VoronoiTesselator

middleware = [
    Middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    ),
]

routes = [
    Route("/", HomePage, methods=["GET"]),
    Route("/{project_id}/columns", geometries, methods=["GET"]),
    Route("/{project_id}/lines", Lines, methods=["GET", "PUT"]),
    Route("/{project_id}/points", Points, methods=["GET", "PUT"]),
    Route("/{project_id}/voronoi", VoronoiTesselator, methods=["PUT", "POST"]),
    Route("/projects", ProjectsAPI, methods=["GET", "POST", "PUT"]),
    Route("/import", import_topologies, methods=["POST"]),
    Route("/{project_id}/col-groups", ColumnGroups, methods=["GET", "POST", "PUT"]),
    Route("/get-line", get_line, methods=["POST"]),
    Route("/{project_id}/csv", get_csv, methods=["GET"]),
]

app = Starlette(routes=routes, debug=True, middleware=middleware)


# On startup, create tables if needed
@app.on_event("startup")
async def startup_event():
    from ..database import Database

    db = Database(DATABASE)
    db.create_project_table()
