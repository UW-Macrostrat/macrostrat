INSERT INTO map_digitizer.linework(geometry, type) VALUES (
    ST_Multi(ST_GeomFromGeoJSON(:geometry_)),
    'default'
);