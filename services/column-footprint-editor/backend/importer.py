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

class Project:
    """ Helper class to pass around project attributes """

    def __init__(self, id_, name= "", description = "") -> None:
        self.id= id_
        self.name = name
        self.description = description

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
    
    def __init__(self, project_id: int, name: str, description: str):
        self.project = Project(project_id, name, description)
        self.db = Database(self.project)

    def get_project_json(self):
        project_id = self.project.id
        url = f'https://macrostrat.org/api/v2/columns?project_id={project_id}&format=geojson_bare'
        res = requests.get(url)
        data = res.json()
        if len(data['features']) > 0:
            return data
        
        url = f'https://macrostrat.org/api/v2/columns?project_id={project_id}&format=geojson_bare&status_code=in%20process'
        res = requests.get(url)
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

            params['name'] = self.project.name
            params['description'] = self.project.description

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





