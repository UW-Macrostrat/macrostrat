## Test import script
from importer import ProjectImporter
from utils import run_docker_config

if __name__ == "__main__":
    ## Command to call topo update in docker

    Importer = ProjectImporter("url", 1)

    #Importer.tear_down_project()
    
    run_docker_config(1, "create_tables")

    
   

