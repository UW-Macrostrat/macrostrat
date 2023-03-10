Map ingestion directory /data/map-ingestion
User group map-ingestion

# Uploading files (from a Windows machine)

Zip up all map files

Copy them to the server

```cd ```

```pscp <map-name.zip> <user>@next.macrostrat.org:/data/map-ingestion/candidates```

# Preparing the data the server 

Enter the PuTTY command line

- Move to the proper directory: `cd /data/map-ingestion/candidates`

- `ls` to see what is in the directory

- Unzip the map and remove the zip file
  - `unzip <map-name>.zip`
  - `rm <map-name>.zip`
- Check to ensure that there is a folder with the proper name:
  -  `ls`
  - If you need to rename the folder: `mv <old> <new>`

## Ingesting the map

The Macrostrat map ingestion app is now accessible using the `macrostrat maps`
command (note to Kate: this has changed! It now works without the dot and `sudo`, and can be run from any directory)


There are a few ways to run the ingestion command:

If you are in the `/data/map-ingestion` directory, and the Shapefiles are directly in the `/data/map-ingestion/candidates/<map-name>` folder:
```macrostrat maps ingest <map-name> candidates/<map-name>/*.shp```

If you are in a folder with Shapefiles:
```macrostrat maps ingest <map-name> *.shp```

If you are in the `/data/map-ingestion/candidates` directory and want to ingest all Shapefiles in the tree:
```macrostrat maps ingest <map-name> <map-name>/**/*.shp```

## Preparing fields for manual data entry

```macrostrat maps prepare-fields <map-name>```

 Then you should be ready to go!