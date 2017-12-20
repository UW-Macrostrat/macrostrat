DELETE FROM lookup_::scale::
WHERE map_id IN (
  SELECT map_id
  FROM maps.::scale::
  WHERE source_id = ::source_id::
);

DELETE FROM maps.map_liths
WHERE map_id IN (
  SELECT map_id
  FROM maps.::scale::
  WHERE source_id = ::source_id::
);

DELETE FROM maps.map_strat_names
WHERE map_id IN (
  SELECT map_id
  FROM maps.::scale::
  WHERE source_id = ::source_id::
);

DELETE FROM maps.map_units
WHERE map_id IN (
  SELECT map_id
  FROM maps.::scale::
  WHERE source_id = ::source_id::
);

DROP TABLE IF EXISTS sources.::primary_table::;
DROP TABLE IF EXISTS sources.::primary_line_table::;

DELETE FROM maps.sources
WHERE source_id = ::source_id::;

DELETE FROM maps.::scale::
WHERE source_id = ::source_id::;

DELETE FROM lines.::scale::
WHERE source_id = ::source_id::;

DELETE FROM points.points
WHERE source_id = ::source_id::;
