SET search_path = public, topology, pg_catalog;

DELETE FROM carto_new.::scale::
WHERE ST_Intersects(geom, (
  SELECT web_geom
  FROM maps.sources
  WHERE source_id = ::source_id::
));

DELETE FROM carto_new.lines_::scale::
WHERE ST_Intersects(geom, (
  SELECT web_geom
  FROM maps.sources
  WHERE source_id = ::source_id::
));
