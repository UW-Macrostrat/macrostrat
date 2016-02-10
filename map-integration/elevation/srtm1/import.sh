for file in downloads/*; do raster2pgsql -s 4326 -a -I -t 30x30 $file sources.srtm1 | psql -U john elevation; done
