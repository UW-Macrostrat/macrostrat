Map ingestion directory /data/map-ingestion
User group map-ingestion

# Uploading files (from a Windows machine)

Zip up all map files

Copy them to the server

```cd <directory>```

```pscp <source-file.zip> <user>@next.macrostrat.org:/data/map-ingestion/candidates```

# On the server (in PuTTY command line)

```cd /data/map-ingestion/candidates```

- `ls` to see what is in the directory

- `unzip <Map>.zip`
- `rm <Map>.zip`

If you need to rename the folder
- `mv <old> <new>`

- `cd ..` (to go into `/data/map-ingestion`)

- `sudo ./map-ingestion` (we will make this better soon).

- `sudo ./map-ingestion ingest <map-name> candidates/<map-name>/*.shp` (sometimes it will be `*.gdb`)

Prepare fields for ingestion

- `sudo ./map-ingestion prepare-fields al_alabaster`

 Then you should be ready to go!