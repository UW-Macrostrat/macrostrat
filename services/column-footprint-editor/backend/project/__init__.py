from pathlib import Path
from database import Database
import requests

here = Path(__file__).parent / ".." / "database"
queries = here / "queries"


class Project:
    """ Helper class to pass around project attributes """

    def __init__(self, id_: int = None, name: str = "", description: str = "") -> None:
        self.id= id_
        self.name = name
        self.description = description
        self.db = Database(self)

    def create_new_project(self):
        if not self.project_in_db():
            self.id = self.db.get_next_project_id()
            self.insert_project_info()
            self.db.create_project_schema()
    
    def project_in_db(self):
        if self.id is not None:
            q = queries / "does-project-exist.sql"
            data = self.db.exec_query(q, params={"project_id": self.id}).to_dict(orient="records")
            return data[0]['exists']  
        else:
            return False

    def insert_project_info(self):
        params = {}
        params['project_id'] = self.id
        params['name'] = self.name
        params['description'] = self.description

        self.db.insert_project_info(params)
    
    def insert_project_column_groups(self):
        route = f'https://macrostrat.org/api/defs/groups?project_id={self.id}'

        res = requests.get(route)
        json_ = res.json()
        data = json_['success']['data']
        for column in data:
            params = {}
            params['col_group_id'] = column['col_group_id']
            params['col_group'] = column['col_group']
            params['col_group_name'] = column['name'] 

            self.db.insert_project_column_group(params)

    def remove_project(self):
        self.db.remove_project()




