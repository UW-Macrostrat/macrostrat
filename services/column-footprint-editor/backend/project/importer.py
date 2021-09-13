import requests
import json
from project import Project


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
            "col_name": properties["col_name"], "col_group_id": properties['col_group_id'],
            "col_id": properties['col_id'],
            "location": loc}
            params['columns'] = 'columns'

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