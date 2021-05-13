INSERT INTO map_digitizer.linework(geometry) VALUES (
    ST_Multi(ST_GeomFromGeoJSON(:geometry_))
);