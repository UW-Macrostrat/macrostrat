SELECT 
	col_name,
	description notes, 
	col_group,
	st_asewkt(geometry) poly_geom,
	st_asewkt(st_snaptogrid(st_centroid(geometry),0.1)) coordinate,
	st_astext(st_snaptogrid(st_centroid(geometry),0.1)) wkt,
	round(st_x(st_centroid(geometry))::numeric,3) long, 
	round(st_y(st_centroid(geometry))::numeric,3) lat  
FROM ${project_schema}.column_map_face;