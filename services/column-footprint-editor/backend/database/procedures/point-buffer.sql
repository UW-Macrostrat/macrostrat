WITH a AS(
    SELECT ST_Buffer(ST_GeomFromGeoJSON(:points), :radius, :quad_segs) as buffered_point
),
b AS (
    SELECT 
        geometry as bounds
    FROM ${topo_schema}.map_face, a WHERE st_intersects(geometry, a.buffered_point)
) SELECT
    st_asgeojson(st_dump(st_difference(
        st_snaptogrid(a.buffered_point, 0.001), 
        st_snaptogrid(b.bounds, 0.001)))) as buffered
    FROM b,a;