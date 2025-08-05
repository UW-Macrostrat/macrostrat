import json
import simplejson
from pathlib import Path
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse, PlainTextResponse

from .utils import clean_change_set
from ..database import Database
from ..project import Project
from ..project.importer import ProjectImporter

here = Path(__file__).parent / ".."
procedures = here / "database" / "procedures"
queries = here / "database" / "queries"
config = here / "config"


class Lines(HTTPEndpoint):
    async def get(self, request):
        project_id = request.path_params["project_id"]
        project = Project(project_id)
        db = Database(project)

        if "id" in request.query_params:
            id_ = request.query_params["id"]

            q = queries / "select-line-by-id.sql"
            sql = open(q).read()

            df = db.exec_query(sql, params={"id_": id_})
            lines = []
            for i in range(0, len(df["lines"])):
                obj = {}
                obj["geometry"] = json.loads(df["lines"][i])
                obj["type"] = "Feature"
                obj["properties"] = {"id": int(df["id"][i])}
                lines.append(obj)

            return JSONResponse({"type": "FeatureCollection", "features": lines})

        q = queries / "get-linework.sql"
        sql = open(q).read()

        df = db.exec_query(sql)

        lines = []
        for i in range(0, len(df["lines"])):
            obj = {}
            obj["geometry"] = json.loads(df["lines"][i])
            obj["type"] = "Feature"
            obj["properties"] = {"id": int(df["id"][i])}
            lines.append(obj)

        return JSONResponse({"type": "FeatureCollection", "features": lines})

    async def put(self, request):
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

        data = await request.json()

        project_id = data["project_id"]
        project = Project(project_id)
        db = Database(project)

        new_change_set = clean_change_set(data["change_set"])
        data["change_set"] = new_change_set

        try:
            for line in data["change_set"]:
                if line["action"] == "change_coordinates":

                    geometry_ = json.dumps(line["feature"]["geometry"])
                    id_ = line["feature"]["properties"]["id"]
                    params = {"geometry_": geometry_, "id_": id_}

                    db.run_sql_file(change_line_file, params)

                if line["action"] == "draw.delete":
                    id_ = line["feature"]["properties"]["id"]
                    db.run_sql_file(delete_line_file, {"id_": id_})

                if line["action"] == "draw.create":
                    geometry_ = json.dumps(line["feature"]["geometry"])
                    db.run_sql_file(create_line_file, {"geometry_": geometry_})

            db.update_topology()
            return JSONResponse({"status": "success"})
        except:
            return JSONResponse(
                {"status": "error", "message": "different data structured expected"}
            )


class Points(HTTPEndpoint):
    async def get(self, request):
        project_id = request.path_params["project_id"]
        project = Project(project_id)
        db = Database(project)

        q = queries / "get-points.sql"
        sql = open(q).read()

        df = db.exec_query(sql)
        cols = df.to_dict(orient="records")
        cols = json.loads(simplejson.dumps(cols, ignore_nan=True))

        json_ = []
        for i in cols:
            if i["point"] is None:
                continue
            obj = {}
            obj["geometry"] = json.loads(i["point"])
            i.pop("point")
            obj["properties"] = i
            json_.append(obj)

        return JSONResponse({"type": "FeatureCollection", "features": json_})

    async def put(self, request):
        """possible actions:
            1. Update Point
            2. Delete Point
            3. Create Point

        This will have to change point geometries in column table and in the data.polygon table
        """
        return JSONResponse({"Success": "Work in progress", "Come back": "Soon"})


def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True


async def get_line(request):
    """a utility function to return a linestring or multilinestring
    For adding an exsiting geometry on the frontend
    """
    res = await request.json()
    data = res["location"]

    location_parser = "ST_GeomFromText(%(location)s)"

    sql = f"SELECT ST_AsGeoJSON(((ST_Dump(ST_Boundary({location_parser}))).geom))"

    db = Database()
    df = db.exec_query(sql, params={"location": data})
    location = json.loads(df.to_dict(orient="records")[0]["st_asgeojson"])

    return JSONResponse({"status": "success", "location": location})


async def geometries(request):

    project_id = request.path_params["project_id"]
    project = Project(project_id)
    db = Database(project)

    q = queries / "get-topology-columns.sql"
    sql = open(q).read()

    df = db.exec_query(sql)
    cols = df.to_dict(orient="records")
    cols = json.loads(simplejson.dumps(cols, ignore_nan=True))

    json_ = []
    for i in cols:
        obj = {}
        obj["geometry"] = json.loads(i["polygon"])
        i.pop("polygon")
        obj["properties"] = i
        json_.append(obj)

    return JSONResponse({"type": "FeatureCollection", "features": json_})


async def get_csv(request):
    project_id = request.path_params["project_id"]
    project = Project(project_id)

    sql = """SELECT ST_AsGeoJSON(c.geometry) polygon,
             ST_AsGeoJSON(c.point) point,
             c.id,
             c.project_id,
             c.col_id,
             c.col_name,
             c.col_group_id,
             c.col_group,
             c.col_group_name
            from ${project_schema}.column_map_face c; """
    df = project.db.exec_query(sql)
    csv = df.to_csv()

    return PlainTextResponse(csv)


async def import_topologies(request):
    data = await request.json()

    if "project_id" not in data:
        return JSONResponse({"error": "project_id not passed"})

    name = None
    description = None
    if "name" in data:
        name = data["name"]
    if "description" in data:
        description = data["description"]

    project_id = int(data["project_id"])

    Importer = ProjectImporter(project_id, name, description)

    Importer.import_column_topology()

    return JSONResponse(
        {"status": "success", "imported": True, "project_id": project_id}
    )
