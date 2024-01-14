/**
Script to create record in maps.{polygons,lines,points} from a record in sources.{slug}_{polygons,lines,points}
*/

DELETE FROM maps.polygons WHERE source_id = {source_id};
DELETE FROM maps.lines WHERE source_id = {source_id};
DELETE FROM maps.points WHERE source_id = {source_id};

INSERT INTO maps.polygons (
  source_id,
  scale,
  orig_id,
  name,
  strat_name,
  age,
  lith,
  descrip,
  comments,
  t_interval,
  b_interval,
  geom
)
SELECT 
  source_id,
  {scale}::macrostrat.map_scale,
  orig_id,
  name,
  geom.
  strat_name,
  age,
  lith,
  descrip,
  comments,
  t_interval,
  b_interval
FROM sources.{slug}_lines
WHERE source_id = {source_id};


INSERT INTO maps.lines (
  source_id,
  scale,
  orig_id,
  name,
  type,
  direction,
  descrip,
  geom
)
SELECT 
  source_id,
  {scale}::macrostrat.map_scale,
  orig_id,
  name,
  type,
  direction,
  descrip,
  geom
FROM sources.{slug}_lines
WHERE source_id = {source_id};


INSERT INTO maps.points (
  source_id,
  strike,
  dip,
  dip_dir,
  point_type,
  certainty,
  comments,
  geom,
  orig_id
)
SELECT 
  source_id,
  strike,
  dip,
  dip_dir,
  point_type,
  certainty,
  comments,
  geom,
  orig_id
FROM sources.{slug}_points
WHERE source_id = {source_id};