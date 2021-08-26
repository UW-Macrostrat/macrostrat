from os import error
from pandas.core.indexing import convert_from_missing_indexer_tuple
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route
from pathlib import Path
import json
import simplejson
import uvicorn

from utils import change_set_clean

from database import Database
from importer import ProjectImporter, Project

here = Path(__file__).parent
procedures = here / "procedures"
config = here / "config"


middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*']),
]

async def homepage(request):
    return PlainTextResponse("Home Page")

async def new_project(request):
    res = await request.json()

    db = Database()
    next_id = db.get_next_project_id()

    params = res['data']
    params['id'] = next_id
    project = Project(params['id'], params['name'], params['description'])

    try:
        project.create_new_project()
        return JSONResponse({"status":"success", "project_id": params['id'], "name": params['name'], "description": params['description']})
    except:
        return JSONResponse({"status": "error"},status_code=404)

async def geometries(request):

    project_id = request.path_params['project_id']
    project = Project(project_id)
    db = Database(project)


    q = here / "queries" / "get-topology-columns.sql"
    sql = open(q).read()

    df = db.exec_query(sql)
    cols = df.to_dict(orient="records")
    cols = json.loads(simplejson.dumps(cols, ignore_nan=True))

    json_ = []
    for i in cols:
        obj = {}
        obj['geometry'] = json.loads(i['polygon'])
        i.pop('polygon')
        obj['properties'] = i
        json_.append(obj)

    return JSONResponse({"type": "FeatureCollection", "features": json_})

async def new_col_group(request):
    """ Endpoint for new Column Groups """

    sql = """INSERT INTO column_groups(col_group_id, col_group, col_group_name)VALUES(
        :col_group_id,:col_group,:col_group_name
    )  """
    db = Database() 

    res = await request.json()

    params = res['updatedModel']
    params['col_group_id'] = db.get_next_col_group_id()

    try:
        db.run_sql(sql, params)
    except error:
        return JSONResponse({"error": str(error)})
    
    return JSONResponse({"status":"success", "col_group_id": params['col_group_id']})

async def property_updates(request):
    """ This will need a route for creating a new column group """

    sql_fn = procedures / "update-properties.sql"
    
    res = await request.json()

    project_id = request.path_params['project_id']
    project = Project(project_id)
    db = project.db

    data = res['updatedModel']
    

    params = dict(id = data['identity_id'], col_name = data['col_name'])
    params = {**params, **dict(col_group_id = data['col_group_id'])}
    params['project_id'] = project_id
    params['location'] = json.dumps(data['location'])

    if params['id'] == 'null':
        params['col_id'] = None
        sql_fn = procedures / "new-column.sql"

    try:
        db.run_sql_file(sql_fn, params)
    except error:
        print(error)
        return JSONResponse({"status": "error", "message": f'{error}'})
    
    return JSONResponse({"statue": f'success'})

async def updates(request):
    """
    This endpoint recieves a changeset from the frontend. 
    It will directly update the map_digitizer.linework
    table. 

    possible actions:
        "change_coordinates",
        "draw.delete",
        "draw.create",

    """
    delete_line_file = procedures / "delete-line.sql"
    change_line_file = procedures / "change-line-coordinates.sql"
    create_line_file = procedures / "create-line.sql"

    project_id = request.path_params['project_id']
    project = Project(project_id)
    db = Database(project)


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
                
        db.update_topology()
        return JSONResponse({"status": "success"})
    except:
        return JSONResponse({"status": "error", "message": "different data structured expected"})

async def import_topologies(request):
    data = await request.json()

    if 'project_id' not in data:
        return JSONResponse({"error": "project_id not passed"})
    
    name = None
    description = None
    if 'name' in data:
        name = data['name']
    if 'description' in data:
        description = data['description']

    project_id = int(data['project_id'])

    Importer = ProjectImporter(project_id, name, description)

    Importer.import_column_topology()

    return JSONResponse({"status": "success","imported":True, "project_id": project_id})

async def project(request):
    """ endpoint to get availble projects """
    db = Database()
    
    project_data = db.get_project_info()
    
    return JSONResponse({"data": project_data})

async def column_groups(request):
    """ 
     endpoint to get column group metadata 
    
    needs to get column groups based on:
        col_group_id
        project_id
        all 
    """
    query_params = request.query_params
    if 'project_id' in query_params:
        id_ = query_params['project_id']
        project = Project(id_)
        sql = '''SELECT DISTINCT cg.* from ${project_schema}.columns c 
                    LEFT JOIN column_groups cg
	                ON cg.col_group_id = c.col_group
                    WHERE cg.col_group_id IS NOT NULL;'''
        try:
            df = project.db.exec_query(sql)
            col_groups = df.to_dict(orient='records')

            return JSONResponse({"status":"success", "data": col_groups})
        except error:
            return JSONResponse({"error": f"project {id_} does not exist"}) 
    
    if 'col_group_id' in query_params:
        id_ = query_params['col_group_id']
        sql = f'''SELECT * FROM column_groups WHERE col_group_id = {id_};'''
        
        try:
            df = Database().exec_query(sql)
            col_groups = df.to_dict(orient='records')
            
            return JSONResponse({"status":"success", "data": col_groups})
        except error:
            return JSONResponse({"error": f"col_group {id_} does not exist"}) 

    if 'all' in query_params:
        sql = 'SELECT * FROM column_groups;'
        df = Database().exec_query(sql)
        col_groups = df.to_dict(orient='records')
            
        return JSONResponse({"status":"success", "data": col_groups})

    base = {}
    base['status'] = 'success'
    base['params'] = [{'col_group_id': "A specific col_group_id", 
                        'example': "?col_group_id=66"},
                      {'project_id': "Get all col_groups associated with a project",
                      'example': '?project_id=1'}]

    return JSONResponse(base)



async def lines(request):

    project_id = request.path_params['project_id']
    project = Project(project_id)
    db = Database(project)


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
    Route('/{project_id}/columns', geometries, methods=['GET']),
    Route('/{project_id}/lines', lines, methods=['GET']),
    Route('/{project_id}/updates', updates, methods=['PUT']),
    Route('/{project_id}/property_updates', property_updates, methods=['PUT']),
    Route('/import', import_topologies, methods=['POST']),
    Route('/projects', project, methods=['GET']),
    Route('/new-project', new_project,methods=['POST']),
    Route('/col-groups', column_groups, methods=["GET"]),
    Route('/col-groups/post', new_col_group, methods=['POST'])
]

app = Starlette(routes=routes,debug=True, middleware=middleware)

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)

