## Test import script
from importer import ProjectImporter
from utils import run_docker_config
from database import Database

if __name__ == "__main__":
    ## Command to call topo update in docker
    project_id = 10
    db = Database(project_id)
    #db.remove_project()

    url = "https://macrostrat.org/api/v2/columns?project_id=10&format=geojson_bare&status_code=in%20process";

    Importer = ProjectImporter(url, project_id)
    
    Importer.import_column_topology()
    
   

