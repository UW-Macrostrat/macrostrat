import requests
import json
from project import Project
from settings import IMPORTER_API

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
        self.db = self.project.db
        self.base_url = IMPORTER_API
    def get_project_json(self):
        project_id = self.project.id
        url = f'{self.base_url}cols?project_id=eq.{project_id}'
        res = requests.get(url)
        data = res.json()

        return data

    def columns_import(self):
        data = self.get_project_json()
        features = data
        
        for feature in features:
            loc = json.dumps(feature['poly_geom'])
            params = {"project_id": feature['project_id'],
            "col_name": feature["col_name"], "col_group_id": feature['col_group_id'],
            "col_id": feature['id'],
            "location": loc}
            params['point'] = json.dumps(feature['coordinate'])
            params['columns'] = 'columns'

            if json.loads(params['location']) is None:
                self.db.insert_project_data(params, no_location=True)
            else:
                self.db.insert_project_data(params)

    def import_column_topology(self):
        """ 
        Method called in API. Performs 
        """
        self.db.create_project_schema()
        self.project.insert_project_info()
        self.project.insert_project_column_groups()
        self.columns_import()
        self.db.on_project_insert()
        self.db.update_topology()
        self.db.redump_linework_from_edge()
        self.db.update_topology()