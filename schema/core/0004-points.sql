CREATE SCHEMA points;

CREATE VIEW points.points AS
 SELECT points.source_id,
    points.strike,
    points.dip,
    points.dip_dir,
    points.point_type,
    points.certainty,
    points.comments,
    points.geom,
    points.point_id,
    points.orig_id
   FROM maps.points;


