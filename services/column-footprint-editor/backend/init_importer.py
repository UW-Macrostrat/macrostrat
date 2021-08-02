## Test import script
from importer import ProjectImporter, Project
from utils import run_docker_config
from database import Database

if __name__ == "__main__":
    ## Command to call topo update in docker
    name = "Test New project"
    description = "Testing.... Testing.... "
    db = Database()
    project_id = db.get_next_project_id()
    project= Project(project_id, name, description)
    project.create_new_project()

    # url = "https://macrostrat.org/api/v2/columns?project_id=10&format=geojson_bare&status_code=in%20process";

    # Importer = ProjectImporter(project_id, name, description)
    
    # Importer.import_column_topology()
    
   

