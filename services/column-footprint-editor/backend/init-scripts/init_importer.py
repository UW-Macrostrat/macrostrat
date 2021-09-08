## Test import script
from importer import ProjectImporter, Project
from utils import run_docker_config
from database import Database
import simplejson
import json

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError as e:
    return False
  return True

if __name__ == "__main__":
    # ids = [6]
    # for i in ids:
    #     project = Project(i)
    #     project.remove_project()
    

    
    # id_ = 10
    # name = "North American Ediacaran"
    # description = "Composite columns of intermediate scale resolution that are comprehensive for the Ediacaran System of present-day North America and adjacent continental blocks formerly part of North America. Compiled by D. Segessenman as part of his Ph.D."

    # importer = ProjectImporter(id_, name, description)
    # importer.import_column_topology()

    # project = Project(10)
    # sql = """ SELECT ST_AsGeoJSON(geometry) polygon, id, project_id, col_id, col_name, col_group_id, col_group, col_group_name, col_color from ${project_schema}.column_map_face c;"""
    # df = project.db.exec_query(sql)

    # cols = df.to_dict(orient="records")
    # cols = json.loads(simplejson.dumps(cols, ignore_nan=True))
    # print(cols)

    data = '''{
        "type": "Polygon",
        "coordinates": [
          [
            [
              66.796875,
              54.97761367069628
            ],
            [
              73.125,
              43.58039085560784
            ],
            [
              96.328125,
              51.39920565355378
            ],
            [
              96.328125,
              57.136239319177434
            ],
            [
              76.640625,
              60.06484046010452
            ],
            [
              66.796875,
              54.97761367069628
            ]
          ]
        ]
    }'''
    
    location_parser = "ST_GeomFromText(%(location)s)"
    if is_json(data):
        location_parser = "ST_GeomFromGeoJSON(%(location)s)"
    
    sql = f"SELECT ST_AsGeoJSON(ST_Multi((ST_Dump(ST_Boundary({location_parser}))).geom))"

    db = Database()
    df = db.exec_query(sql, params={'location':data}) 
    location = df.to_dict(orient="records")[0]['st_asgeojson']

    print(location)