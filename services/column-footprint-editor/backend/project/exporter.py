import requests
import json
from settings import EXPORTER_API
from project import Project
from pathlib import Path


here = Path(__file__).parent / ".." / "database"
queries = here / "queries"

class ProjectExporter:
    '''
    Class for Exporting projects to macrostrat

    There are two cases:
        1) Project starts in birdseye
            - this is easy, EVERYTHING must be inserted into macrostrat
        2) Project starts from macrostrat
            - NOT as easy, some may need insertions while others neeed updates.
            - Project name being edited, col-groups being edited, cols being edited.
            - ITS A PAIN

    '''
    
    rep_header = {"Prefer": "return=representation"}
    base_url = EXPORTER_API
    cols_export = queries / "cols-export.sql"

    def __init__(self, project_id: int, name: str="", description: str=""):
        self.project = Project(project_id, name, description)
        self.db = self.project.db
        self.project_sql = f'SELECT * FROM projects WHERE project_id = {project_id}'
    
    def export_new_project(self):
        """ where project began in birdseye, all insertions """

        ## insert project get id
        project = self.db.exec_sql(self.project_sql, count=1)
        data = {"project": project.name, "descrip":project.description, 'timescale_id': 1 }

        # we will assume that res is the project object, not a list of one object
        res = requests.post(self.base_url + "projects", headers=self.rep_header, data=data)
        res = res.json()
        project_id = res[0]['id']

        ## insert col-groups get ids and names (need project_id)
            ## use hash-table to store  {col-group-name: col-group-id}
            ## for col insertions
        col_group_sql = """ SELECT col_group, col_group_name  FROM ${project_schema}.column_groups; """
        col_groups = self.db.exec_sql(col_group_sql)
        col_group_lookup = {}
        for col_group in col_groups:
            data = {"col_group": col_group.col_group, "col_group_long": col_group.col_group_name, "project_id": project_id}
            res = requests.post(self.base_url + "col_groups", headers=self.rep_header, data=data)
            res = res.json()
            col_group_lookup[res[0]['col_group']] = res[0]['id']

        ## insert columns (need project_id and col-group-id)
        col_sql = open(self.cols_export).read()
        cols = self.db.exec_sql(col_sql)
        col_num = 1
        for col in cols:
            #col_group_id, project_id, col_type, col, col_name, lat, long, coordinate, wkt, poly_geom, notes
            params = {"col_group_id": col_group_lookup[col.col_group], "project_id": project_id}
            params = {**params, "col_type": "section","col": col_num, "lng": col.long, "lat": col.lat }
            params = {**params, "coordinate": col.coordinate, "wkt": col.wkt, "poly_geom": col.poly_geom}
            params['notes'] = col.notes
            params['col_name']=col.col_name
            params['status_code'] = 'in process'
            requests.post(self.base_url + "cols", data=params)
            col_num += 1

    def export_edited_project(self):
        """ project began in macrostrat, updates and insertions """

        ## project ==> update name and description
        
        ## for col-groups that exist (col-group-id-macrostrat), update info
        ## for col-groups that don't exist, insertion! (need project_id)
            # keep track same way through hash-table

        ## for cols that exist, i.e col_id is not None, update (col-group may need updating)
        ## otherwise insert! (project_id, col-group-id)
