WITH a AS(
SELECT (
    st_dump(st_voronoipolygons(points,0.0, c.geometry))).geom as voronoi,
     c.geometry as bounds
FROM 
(
    SELECT ST_GeomFromGeoJSON(:points) as points
    ) as g
    JOIN ${project_schema}.column_map_face c
    ON ST_Contains(c.geometry, points)
) SELECT 
    st_asgeojson(st_dump(st_intersection(a.voronoi, a.bounds)))
     as voronoi FROM a;

