import requests
import json
from project import Project


class ProjectExporter:
    '''
    Class for Exporting projects to macrostrat

    Mix of python and SQL

    Steps for exporting:
    1) 

    '''
    
    def __init__(self, project_id: int, name: str, description: str):
        self.project = Project(project_id, name, description)
        self.db = self.project.db