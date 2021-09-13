from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from database import Database
from project import Project
from os import error

class ColumnGroups(HTTPEndpoint):
    async def get(self, request):
        """ 
        endpoint to get column group metadata 
        
        needs to get column groups based on:
            col_group_id
            project_id
            all 
        """

        project_id = request.path_params['project_id']
        project = Project(project_id)

        if 'col_group_id' in request.query_params:
            id_ = request.query_params['col_group_id']
            sql = 'SELECT * FROM ${project_schema}.column_groups WHERE col_group_id = ' + f'{id_};'
            
            try:
                df = Database().exec_query(sql)
                col_groups = df.to_dict(orient='records')
                
                return JSONResponse({"status":"success", "data": col_groups})
            except error:
                return JSONResponse({"error": f"col_group {id_} does not exist"}) 


        sql = '''SELECT * from ${project_schema}.column_groups;'''
        try:
            df = project.db.exec_query(sql)
            col_groups = df.to_dict(orient='records')

            return JSONResponse({"status":"success", "data": col_groups})
        except error:
            return JSONResponse({"error": f"project {project_id} does not exist"}) 


    async def post(self, request):
        """ Endpoint for new Column Groups """

        sql = """INSERT INTO ${project_schema}.column_groups(col_group_id, col_group, col_group_name)VALUES(
            :col_group_id,:col_group,:col_group_name
        )  """

        project = Project(request.path_params['project_id'])

        res = await request.json()

        params = res['updatedModel']
        params['col_group_id'] = project.db.get_next_col_group_id()

        try:
            project.db.run_sql(sql, params)
        except error:
            return JSONResponse({"error": str(error)})
        
        return JSONResponse({"status":"success", "col_group_id": params['col_group_id']})