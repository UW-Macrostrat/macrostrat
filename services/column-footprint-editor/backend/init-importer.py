## Test import script
import subprocess
from importer import ProjectImporter


if __name__ == "__main__":
    ## Command to call topo update in docker
    docker_geologic_update = 'docker exec postgis-geologic-map_app_1 bin/geologic-map update'
    docker_geologic_create_tables = 'docker exec postgis-geologic-map_app_1 bin/geologic-map create-tables --all'
    docker_geologic_reset_topo = 'docker exec postgis-geologic-map_app_1 bin/geologic-map reset'

    project_id = 10
    url = "https://macrostrat.org/api/v2/columns?project_id=10&format=geojson_bare&status_code=in%20process"

    Importer = ProjectImporter(url, project_id)

    # remove topology and truncate columns, linework, polygon tables
    Importer.tear_down_project()
    p = subprocess.Popen(docker_geologic_reset_topo.split())
    p.wait()


    # # rebuild the map_topolgy schema
    p = subprocess.Popen(docker_geologic_create_tables.split())
    p.wait()

    # fetches columns from macrostrat
    # inserts in columns.columns
    # runs import.sql
    #   creates identity polygons using ST_PointOnSurface
    #   adds topolgy column to columns.columns
    #   adds location to topology
    #   dumps edge_data to linework table
    Importer.import_column_topolgy()

    # Importer.create_map_face_view()

    # # runs the geologic-map update command in docker
    # p = subprocess.Popen(docker_geologic_update.split())
    # p.wait()
    
   

