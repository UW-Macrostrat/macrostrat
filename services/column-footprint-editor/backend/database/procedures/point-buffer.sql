WITH a AS (
    SELECT 
        st_collect(geometry) as bounds
    FROM ${topo_schema}.map_face
) SELECT
    st_asgeojson(st_dump(st_difference(
        ST_Buffer(ST_GeomFromGeoJSON(:points), :radius, :quad_segs), 
        a.bounds))) as buffered
    FROM a;