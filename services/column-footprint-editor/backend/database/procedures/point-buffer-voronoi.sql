/* creates voronoi polygons from overlapping buffered points */
WITH a as (
	SELECT ST_Buffer(
				st_geomfromgeojson(
                      :points
				      ), :radius, :quad_segs
				      )
				       as bounds
				       ),
b as(
	SELECT st_intersection((
		st_dump(st_voronoipolygons(
			st_geomfromgeojson(:points)
		,0.0, a.bounds))).geom, a.bounds) as voronoi
FROM a
),
c as(
	SELECT st_collect(geometry) as bounds from ${topo_schema}.map_face
)
SELECT st_asgeojson(
	st_dump(
		   st_difference(
		   		b.voronoi,
		   		c.bounds
		   ))
	) as buffered FROM b, c;