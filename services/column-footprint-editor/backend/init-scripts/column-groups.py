from database import Database
from requests import get

""" Script to Import All existing Col-groups to macrostrat """

if __name__ == "__main__":
    db = Database()

    route = "https://macrostrat.org/api/defs/groups?all"
    res = get(route)
    json_ =  res.json()
    data = json_['success']['data']
    for column in data:
        params = {}
        params['col_group_id'] = column['col_group_id']
        params['col_group'] = column['col_group']
        params['col_group_name'] = column['name'] 

        sql = """INSERT INTO column_groups(col_group_id, col_group, col_group_name) VALUES(
            :col_group_id, :col_group, :col_group_name);"""
        db.run_sql(sql, params)


