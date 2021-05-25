from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route
from pathlib import Path
import json
import uvicorn

from utils import change_set_clean

from database import Database

here = Path(__file__).parent
procedures = here / "procedures"

db = Database()

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*']),
]


async def homepage(request):
    return PlainTextResponse("Home Page")

async def geometries(request):
    q = here / "queries" / "get-topology-columns.sql"
    sql = open(q).read()

    df = db.exec_query(sql)
    df.fillna('')
    polygons = []
    for i in range(0, len(df['polygon'])):
        obj = {}
        obj['geometry'] = json.loads(df['polygon'][i])
        obj['type'] = "Feature"
        obj['properties'] = {"id": f"{df['id'][i]}","project_id": f"{df['project_id'][i]}", "col_id": f"{df['col_id'][i]}","col_name": df['col_name'][i],"col_group": df['col_group'][i],"col_color": df['col_color'][i]}
        polygons.append(obj)

    return JSONResponse({"type": "FeatureCollection", "features": polygons})

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

                db.run_sql_file(change_line_file, params)

            if line['action'] == "draw.delete":
                print("Delete a Line")
                id_ = line['feature']['properties']['id']
                db.run_sql_file(delete_line_file, {"id_":id_})

            if line['action'] == "draw.create":
                print("Add a line")
                geometry_ = json.dumps(line['feature']['geometry'])
                db.run_sql_file(create_line_file, {"geometry_":geometry_})
        return JSONResponse({"Status": "Success", "change_set": json.dumps(data['change_set'])})
    except:
        return JSONResponse({"Status": "Error", "message": "different data structured expected"})


async def lines(request):

    if 'id' in request.query_params:
        id_ = request.query_params['id']

        q = here / "queries" / "select-line-by-id.sql"
        sql = open(q).read()

        df = db.exec_query(sql, params={'id_': id_})
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

    df = db.exec_query(sql)

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
    Route('/columns', geometries, methods=['GET']),
    Route('/lines', lines, methods=['GET']),
    Route('/updates', updates, methods=['PUT'])
]

app = Starlette(routes=routes,debug=True, middleware=middleware)

if __name__ == "__main__":
    db.print_hello()
    uvicorn.run(app, host='0.0.0.0', port=8000)

