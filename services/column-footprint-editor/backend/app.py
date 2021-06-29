from os import error
import requests
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route
from pathlib import Path
import subprocess
import json
import uvicorn

from utils import change_set_clean, cmd

from database import Database
from importer import ProjectImporter

here = Path(__file__).parent
procedures = here / "procedures"

db = Database()

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*']),
]

## Command to call topo update in docker
docker_geologic_update = 'docker exec postgis-geologic-map_app_1 bin/geologic-map update'
docker_geologic_create_tables = 'docker exec postgis-geologic-map_app_1 bin/geologic-map create-tables --all'
docker_geologic_reset_topo = 'docker exec postgis-geologic-map_app_1 bin/geologic-map reset'


async def homepage(request):
    return PlainTextResponse("Home Page")

async def geometries(request):

    project_id = request.path_params['project_id']

    q = here / "queries" / "get-topology-columns.sql"
    sql = open(q).read()

    df = db.exec_query(sql, project_id = project_id)
    df.fillna('')
    polygons = []
    for i in range(0, len(df['polygon'])):
        obj = {}
        obj['geometry'] = json.loads(df['polygon'][i])
        obj['type'] = "Feature"
        obj['properties'] = {"id": f"{df['id'][i]}","project_id": f"{df['project_id'][i]}", "col_id": f"{df['col_id'][i]}","col_name": df['col_name'][i],"col_group": df['col_group'][i],"col_color": df['col_color'][i]}
        polygons.append(obj)

    return JSONResponse({"type": "FeatureCollection", "features": polygons})

async def property_updates(request):

    sql_fn = procedures / "update-properties.sql"

    res = await request.json()

    project_id = request.path_params['project_id']


    data = res['updatedModel']
    

    params = dict(id = data['identity_id'], column_name = data['column_name'],group = data['group'])
    try:
        db.run_sql_file(sql_fn, params, project_id = project_id)
    except error:
        print(error)
        return JSONResponse({"status": "error", "message": f'{error}'})
    
    return JSONResponse({"statue": f'success'})

async def updates(request):
    """
    This endpoint recieves a changeset from the frontend. 
    It will directly update the map_digitizer.linework
    table. 

    data = {change_set: [{objects}]}

    possible actions:
        "change_coordinates",
        "draw.delete",
        "draw.create",

    row id = object['feature']['properties']['id']
    geojson = object['feature']['geometry'] 

    Might be good to perform a change_set cleaning to remove duplicates. 
        Will be especially important when someone creates a new line (polygon) and then also moves 
        it around triggering the change_coordinates events. I can use object['feature']['id'], it's the 
        internal id, a very long string 
    """
    delete_line_file = procedures / "delete-line.sql"
    change_line_file = procedures / "change-line-coordinates.sql"
    create_line_file = procedures / "create-line.sql"

    project_id = request.path_params['project_id']


    data = await request.json()

    new_change_set = change_set_clean(data['change_set'])
    data['change_set'] = new_change_set

    try:
        for line in data['change_set']:
            if line['action'] == "change_coordinates":
                print("Changed Coordinates")

                geometry_ = json.dumps(line['feature']['geometry'])
                id_ = line['feature']['properties']['id']
                params = {"geometry_": geometry_, "id_":id_}

                db.run_sql_file(change_line_file, params, project_id = project_id)

            if line['action'] == "draw.delete":
                print("Delete a Line")
                id_ = line['feature']['properties']['id']
                db.run_sql_file(delete_line_file, {"id_":id_}, project_id = project_id)

            if line['action'] == "draw.create":
                print("Add a line")
                geometry_ = json.dumps(line['feature']['geometry'])
                db.run_sql_file(create_line_file, {"geometry_":geometry_}, project_id = project_id)

        p = subprocess.run(docker_geologic_update.split())
        return JSONResponse({"status": "success"})
    except:
        return JSONResponse({"status": "error", "message": "different data structured expected"})

async def import_topologies(request):
    data = await request.json()

    if 'url' not in data:
        return JSONResponse({"error": "url not passed"})
    if 'project_id' not in data:
        return JSONResponse({"error": "project_id not passed"})

    url = data['url']
    project_id = data['project_id']

    Importer = ProjectImporter(url, project_id)

    # p = subprocess.Popen(docker_geologic_reset_topo.split())
    # p.wait()

    Importer.tear_down_project()

    # p = subprocess.Popen(docker_geologic_create_tables.split())
    # p.wait()

    Importer.import_column_topolgy()

    Importer.create_map_face_view()

    return JSONResponse({"status": "success","imported":True, "project_id": project_id, "url": url})


async def lines(request):

    project_id = request.path_params['project_id']

    if 'id' in request.query_params:
        id_ = request.query_params['id']

        q = here / "queries" / "select-line-by-id.sql"
        sql = open(q).read()

        df = db.exec_query(sql, params={'id_': id_}, project_id = project_id)
        lines = []
        for i in range(0, len(df['lines'])):
            obj = {}
            obj['geometry'] = json.loads(df['lines'][i])
            obj['type'] = "Feature"
            obj['properties'] = {"id": int(df['id'][i])}
            lines.append(obj)

        return JSONResponse({"type": "FeatureCollection", "features": lines})


    q = here / "queries" / "get-linework.sql"
    sql = open(q).read()

    df = db.exec_query(sql, project_id = project_id)

    lines = []
    for i in range(0, len(df['lines'])):
        obj = {}
        obj['geometry'] = json.loads(df['lines'][i])
        obj['type'] = "Feature"
        obj['properties'] = {"id": int(df['id'][i])}
        lines.append(obj)

    return JSONResponse({"type": "FeatureCollection", "features": lines})

routes = [
    Route("/", homepage, methods=['GET']),
    Route('/columns/{project_id}', geometries, methods=['GET']),
    Route('/lines/{project_id}', lines, methods=['GET']),
    Route('/updates/{project_id}', updates, methods=['PUT']),
    Route('/property_updates/{project_id}', property_updates, methods=['PUT']),
    Route('/import/{project_id}', import_topologies, methods=['POST'])
]

app = Starlette(routes=routes,debug=True, middleware=middleware)

if __name__ == "__main__":
    db.print_hello()
    uvicorn.run(app, host='0.0.0.0', port=8000)

