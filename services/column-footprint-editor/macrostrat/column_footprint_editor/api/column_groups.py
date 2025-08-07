from os import error

import simplejson
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse

from ..project import Project
from ..settings import DATABASE


class ColumnGroups(HTTPEndpoint):
    async def get(self, request):
        """
        endpoint to get column group metadata

        needs to get column groups based on:
            col_group_id
            project_id
            all
        """

        project_id = request.path_params["project_id"]
        project = Project(DATABASE, project_id)

        if "id" in request.query_params:
            id_ = request.query_params["id"]
            sql = (
                "SELECT * FROM ${project_schema}.column_groups WHERE id = " + f"{id_};"
            )

            try:
                df = project.db.exec_query(sql)
                col_groups = df.to_dict(orient="records")

                return JSONResponse({"status": "success", "data": col_groups})
            except error:
                return JSONResponse({"error": f"col_group {id_} does not exist"})

        sql = """SELECT * from ${project_schema}.column_groups;"""
        try:
            df = project.db.exec_query(sql)
            col_groups = df.to_dict(orient="records")
            col_groups = simplejson.loads(simplejson.dumps(col_groups, ignore_nan=True))

            return JSONResponse({"status": "success", "data": col_groups})
        except error:
            return JSONResponse({"error": f"project {project_id} does not exist"})

    async def post(self, request):
        """Endpoint for new Column Groups"""

        sql = """INSERT INTO ${project_schema}.column_groups(col_group, col_group_name, color)VALUES(
            :col_group,:col_group_name,:color
        )  """

        project = Project(DATABASE, request.path_params["project_id"])

        res = await request.json()

        params = res["updatedModel"]

        try:
            project.db.run_sql(sql, params)

            sql = "SELECT id FROM ${project_schema}.column_groups WHERE col_group = :col_group"
            res = project.db.exec_sql(sql, params=params, count=1)
            params["col_group_id"] = res.id
        except error:
            return JSONResponse({"error": str(error)})

        return JSONResponse(
            {"status": "success", "col_group_id": params["col_group_id"]}
        )

    async def put(self, request):
        """Endpoint for Editing Existing Column Groups"""

        sql = """
            UPDATE ${project_schema}.column_groups cg
                SET col_group = :col_group,
                col_group_name = :col_group_name,
                color = :color
            WHERE cg.id = :col_group_id
         """
        project = Project(DATABASE, request.path_params["project_id"])

        res = await request.json()

        params = res["updatedModel"]
        if res["updatedModel"].get("color") is None:
            params["color"] = None

        try:
            project.db.run_sql(sql, params)
        except error:
            return JSONResponse({"error": str(error)})

        return JSONResponse({"status": "success", **params})
