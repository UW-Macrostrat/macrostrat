## Test import script
from importer import ProjectImporter, Project
from utils import run_docker_config
from database import Database
import simplejson
import json

if __name__ == "__main__":

    # project = Project(1)
    # project.remove_project()
    # project = Project(3)
    # project.remove_project()
    # project = Project(1010)
    # project.remove_project()
    
    # id_ = 10
    # name = "North American Ediacaran"
    # description = "Composite columns of intermediate scale resolution that are comprehensive for the Ediacaran System of present-day North America and adjacent continental blocks formerly part of North America. Compiled by D. Segessenman as part of his Ph.D."

    # importer = ProjectImporter(id_, name, description)
    # importer.import_column_topology()

    project = Project(10)
    sql = """ SELECT ST_AsGeoJSON(geometry) polygon, id, project_id, col_id, col_name, col_group_id, col_group, col_group_name, col_color from ${project_schema}.column_map_face c;"""
    df = project.db.exec_query(sql)

    cols = df.to_dict(orient="records")
    cols = json.loads(simplejson.dumps(cols, ignore_nan=True))
    print(cols)
    

