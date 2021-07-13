## Test import script
from importer import ProjectImporter, Project
from utils import run_docker_config
from database import Database

if __name__ == "__main__":
    ## Command to call topo update in docker
    project_id = 10
    name = "North America"
    description = "Composite column dataset for the USA and Canada."
    project= Project(project_id, name, description)
    db = Database(project)
    db.remove_project({"project_id":project_id})

    # url = "https://macrostrat.org/api/v2/columns?project_id=10&format=geojson_bare&status_code=in%20process";

    # Importer = ProjectImporter(project_id, name, description)
    
    # Importer.import_column_topology()
    
   

