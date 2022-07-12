from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from database import Database
from project import Project
from pathlib import Path
import json

here = Path(__file__).parent / ".."
procedures = here / "database" /"procedures"
queries= here / "database" / "queries"

class VoronoiTesselator(HTTPEndpoint):
    """ class to turn points and a bounding geometry into a 
        voronoi tesselation.
        To be DRY: we'll have a method that handles the tesselation with the DB

        A get and post will both call this method, however, the get will only return 
        the res to the frontend.
        A post will commit it to the DB
    """

    tesselate_sql = procedures / "tesselate.sql"

    def create_multi_point(self, points):
        string = 'SRID=4326;MULTIPOINT ('
        for i,point in enumerate(points):
            lng,lat = point
            if i == len(points) - 1:
                string += f'{lng} {lat}'
            else:
                string += f'{lng} {lat}, '
        
        return string + ")"

    def tesselate(self, db: Database, points):
        """ need a procedure for st_voronoi 
        points need to be a multipoint geometry
        bounding_geom should be a line or polygon.
        
        I can expect to recieve a list of [lng,lats] for points
        and bounding_geom will probably be geojson
        """
        multi_point = self.create_multi_point(points)

        sql = open(self.tesselate_sql).read()
        res = db.exec_sql(sql, params={"multipoint": multi_point}).fetchall()
        return [json.loads(dict(row)['voronoi']) for row in res]


    async def put(self, request):
        project_id = request.path_params['project_id']
        project = Project(project_id)
        db = Database(project)

        data = await request.json()
        points = data["points"]

        polygons = self.tesselate(db, points)

        return JSONResponse({"Status":"Success", "polygons": polygons})
    
    async def post(self, request):
        project_id = request.path_params['project_id']
        project = Project(project_id)
        db = Database(project)

        return JSONResponse({"Status": "Not implemented yet"})