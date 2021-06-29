import requests
import pandas as pd
import json
from pathlib import Path
import subprocess
import time

from database import Database
from utils import cmd, config_check

here = Path(__file__).parent
queries = here / "queries"
procedures = here / "procedures"
fixtures = here / 'fixtures'
config_dir = here / "config"

docker_geologic_update = 'docker exec postgis-geologic-map_app_1 bin/geologic-map update'

class ProjectImporter:
    '''
    Importer class for importing new projects from macrostrat

    Mix of python and SQL

    Steps for importing
    1. Fetch data from macrostrat
    2. Import project into the columns.columns table
    3. Create a base topology (HOW DOES THIS HAPPEN??)
        - create identity polygons from ST_PointOnSurface for the new polygons

    '''
    
    def __init__(self, url, project_id):
        self.url = url
        self.project_id = project_id
        self.db = Database()
        self.insert_file = queries / "project_insert.sql"
        self.import_sql = procedures / "import.sql"
        self.remove_project_sql = procedures / "remove-project.sql"
        self.redump_lines_sql = procedures / "redump-linework-from-edge-data.sql"
        self.create_view_sql = fixtures / "views.sql"
        config_check(self.project_id)

    def create_project_config(self):
        config = {}
        config['project_schema'] = f'project_{self.project_id}'
        config['data_schema'] = f'project_{self.project_id}_data'
        config['topo_schema'] = f'project_{self.project_id}_topology'

        fn = config_dir / f'project_{self.project_id}.json'
        with open(fn, 'w') as f:
            json.dump(config, f)

    def get_project_json(self):
        res = requests.get(self.url)
        data = res.json()

        return data
    
    def sql_import_procedures(self):
        self.db.run_sql_file(self.import_sql, project_id=self.project_id)
    
    def create_map_face_view(self):
        self.db.run_sql_file(self.create_view_sql, project_id=self.project_id)
    
    def columns_import(self):
        data = self.get_project_json()
        features = data['features']
        
        for feature in features:
            loc = json.dumps(feature['geometry'])
            properties = feature['properties']
            params = {"project_id": properties['project_id'],
            "col_name": properties["col_name"], "col_group": properties['col_group'],
            "col_id": properties['col_id'],
            "location": loc}
            params['columns'] = 'columns'
            self.db.run_sql_file(self.insert_file, params, project_id=self.project_id)
    
    def tear_down_project(self):
        self.db.run_sql_file(self.remove_project_sql, project_id=self.project_id)

    def import_column_topolgy(self):
        self.columns_import()
        self.sql_import_procedures()

        # update again
        #p = subprocess.call(docker_geologic_update, shell=True)
        #cmd(docker_geologic_update)
        time.sleep(20)

        self.db.run_sql_file(self.redump_lines_sql, project_id = self.project_id)

        # # truncate linework and dump edge_data to linework
        # self.db.run_sql_string('TRUNCATE map_digitizer.linework CASCADE')





