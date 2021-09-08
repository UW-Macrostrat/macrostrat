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

    async def post(self, request):
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