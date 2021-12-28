from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from database import Database
from project import Project
from pathlib import Path

from os import error
import json

here = Path(__file__).parent / ".."
procedures = here / "database" /"procedures"
queries= here / "database" / "queries"
config = here / "config"

class ProjectsAPI(HTTPEndpoint):

    async def get(self, request):
        """ endpoint to get availble projects """
        db = Database()
        
        project_data = db.get_project_info()
        
        return JSONResponse({"data": project_data})
    
    async def put(self, request):
        """  """
        sql_fn = procedures / "update-properties.sql"
    
        res = await request.json()

        project_id = res['project_id']
        project = Project(project_id)
        db = project.db

        data = res['updatedModel']
        

        params = dict(id = data.get('identity_id', None), col_name = data['col_name'])
        params = {**params, **dict(col_group_id = data['col_group_id'])}
        params['project_id'] = project_id
        params['location'] = json.dumps(data['location'])

        if params['id'] == 'null' or params['id'] is None:
            params['col_id'] = None
            sql_fn = procedures / "new-column.sql"

        try:
            db.run_sql_file(sql_fn, params)
        except error:
            print(error)
            return JSONResponse({"status": "error", "message": f'{error}'})

        params['location'] = data['location']
        return JSONResponse({"statue": f'success', "project": params})
    
    async def post(self, request):
        res = await request.json()

        db = Database()
        next_id = db.get_next_project_id()

        params = res['data']
        params['id'] = next_id
        project = Project(params['id'], params['name'], params['description'])
        print(params)

        try:
            project.create_new_project()
            return JSONResponse({"status":"success", "project_id": params['id'], "name": params['name'], "description": params['description']})
        except:
            return JSONResponse({"status": "error"},status_code=500)