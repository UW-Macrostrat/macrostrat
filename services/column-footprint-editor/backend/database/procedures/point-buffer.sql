WITH a AS(
    SELECT ST_Buffer(ST_GeomFromGeoJSON(:points), :radius, :quad_segs) as buffered_point
),
b AS (
    SELECT 
        st_collect(geometry) as bounds
    FROM ${topo_schema}.map_face
) SELECT
    st_asgeojson(st_dump(st_difference(
        a.buffered_point, 
        b.bounds))) as buffered
    FROM b,a;