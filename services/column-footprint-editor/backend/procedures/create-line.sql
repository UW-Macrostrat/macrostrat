INSERT INTO ${data_schema}.linework(geometry, type) VALUES (
    ST_Multi(ST_GeomFromGeoJSON(:geometry_)),
    'default'
);