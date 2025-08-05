WITH a as(
    SELECT (ST_Dump(ST_Boundary(ST_GeomFromGeoJSON(:polygon)))).geom as geom
)
INSERT INTO ${data_schema}.linework(geometry, type) 
    SELECT ST_Multi(a.geom),
    'default'
    FROM a;
