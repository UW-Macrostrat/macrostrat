-- Stitch linestrings that are the wrong type, preventing constraint from being added
UPDATE maps.lines SET geom = ST_LineFromMultiPoint(geom)
WHERE ST_GeometryType(geom) = 'ST_MultiPoint'
  AND NOT maps.lines_geom_is_valid(geom);

DELETE FROM maps.lines WHERE NOT maps.lines_geom_is_valid(geom);