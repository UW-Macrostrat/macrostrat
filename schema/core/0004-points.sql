CREATE SCHEMA points;
ALTER SCHEMA points OWNER TO macrostrat;

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

ALTER TABLE points.points OWNER TO macrostrat_admin;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA points GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA points GRANT SELECT ON TABLES  TO macrostrat;
