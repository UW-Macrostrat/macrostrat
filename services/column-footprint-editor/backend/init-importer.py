## importer script to import a json file into database

import json
from pathlib import Path

from database import Database
from utils import pretty_print

db = Database()
here = Path(__file__).parent
queries = here / "queries"

data_dir = here / "data"
json_f = data_dir / "project_10.json"

insert_file = queries / "project_1_insert.sql"

if __name__ == "__main__":
    
    db.print_hello()

    print(__name__)
    # works
    
    sql = open(insert_file).read()
    print(sql)

    json_text = open(json_f).read()

    ## I had to do this not to overload system
    ## should be a pooling configuration for the engine
    json_data = json.loads(json_text) 
    for ele in json_data:
        loc = json.dumps(ele['location'])
        params = {"project_id": ele['project_id'],
         "col_name": ele["col_name"], "col_group": ele['col_group'],
         "col_id": ele['col_id'],
         "location": loc}
        db.run_sql_file(insert_file, params)

