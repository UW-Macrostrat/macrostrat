/*
Creates individual line segmants from polygons. Avoids having a massive line that makes up one polygon

needs 2 parameters

table - table where polygons are
column - column of polygon geometries
*/

SELECT ST_AsText( ST_MakeLine(sp,ep) )
FROM
   -- extract the endpoints for every 2-point line segment for each linestring
   (SELECT
      ST_PointN(geom, generate_series(1, ST_NPoints(geom)-1)) as sp,
      ST_PointN(geom, generate_series(2, ST_NPoints(geom)  )) as ep
    FROM
       -- extract the individual linestrings
      (SELECT (ST_Dump(ST_Boundary(:column))).geom
       FROM :table
       ) AS linestrings
    ) AS segments;