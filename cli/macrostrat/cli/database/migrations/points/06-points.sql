/**
Migrate points to the new schema
*/

ALTER TABLE points.points SET SCHEMA maps;
-- Add foreign key constraint
ALTER TABLE maps.points 
  ADD CONSTRAINT points_source_id_fkey
  FOREIGN KEY (source_id)
  REFERENCES maps.sources (source_id);


CREATE OR REPLACE VIEW points.points AS
SELECT * FROM maps.points;