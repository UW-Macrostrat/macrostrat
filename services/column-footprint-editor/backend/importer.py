import requests
import pandas as pd
import json
from pathlib import Path
import subprocess
import time

from database import Database
from utils import cmd

here = Path(__file__).parent
queries = here / "queries"
procedures = here / "procedures"
fixtures = here / 'fixtures'

docker_geologic_update = 'docker exec postgis-geologic-map_app_1 bin/geologic-map update'

class ProjectImporter:
    '''
    Importer class for importing new projects from macrostrat

    Mix of python and SQL

    Steps for importing
    1. Configuration creation or check (db method)
    2. Schema creations (db method)
    3. Data fetch from macrostrat (import method)
    4. Insert into DB (import & db method)
    5. Dump identity polygons and Lines -> topology created (db method)
    6. Redump linework from edge_data (db method)

    '''
    
    def __init__(self, url, project_id):
        self.url = url
        self.project_id = project_id
        self.db = Database(self.project_id)

    def get_project_json(self):
        res = requests.get(self.url)
        data = res.json()

        return data
    
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
            self.db.insert_project_data(params)

    def import_column_topology(self):
        """ 
        Method called in API. Performs 
        """
        self.db.create_project_schema()
        self.columns_import()
        self.db.on_project_insert()
        self.db.update_topology()
        self.db.redump_linework_from_edge()
        self.db.update_topology()





