--This query adds postgrest via views created.
--allows grant access to users
--adds policies to implement RLS for designated users.

--expose tables as views so postgrest routes are created.
--CRUD ops work
--remove user_id from view so that the column defaults to use the user_id from the jwt
--removed id from the view so that it autoincrements rather than HTTP posts having to handle that value
CREATE OR REPLACE VIEW macrostrat_api.user_locations AS
SELECT
  id,
  user_id,
  name,
  description,
  point,
  zoom,
  meters_from_point,
  elevation,
  azimuth,
  pitch,
  map_layers
FROM user_features.user_locations;
--grant select/read on all columns
GRANT SELECT ON macrostrat_api.user_locations TO web_user;
--grant insert,update,delete only on mutable columns
GRANT INSERT (name, description, point, zoom,
              meters_from_point, elevation, azimuth,
              pitch, map_layers) ON macrostrat_api.user_locations TO web_user;
GRANT UPDATE (name, description, point, zoom,
              meters_from_point, elevation, azimuth,
              pitch, map_layers) ON macrostrat_api.user_locations TO web_user;
GRANT DELETE ON macrostrat_api.user_locations TO web_user;



--READ ONLY
CREATE OR REPLACE VIEW macrostrat_api.location_tags  AS
  SELECT * FROM user_features.location_tags;
--CRUD ops work
CREATE OR REPLACE VIEW macrostrat_api.location_tags_intersect  AS
  SELECT * FROM user_features.location_tags_intersect;


GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.location_tags_intersect TO web_user;
--read only access to predetermined tag list
GRANT SELECT ON macrostrat_api.location_tags TO web_user;
--ask PostgREST to pick up the view changes
NOTIFY pgrst, 'reload schema';


--create the postgrest POLICIES for the location table
ALTER TABLE user_features.user_locations ENABLE ROW LEVEL SECURITY;
--selects only user_id's locations
CREATE POLICY pl_ul_select
ON  user_features.user_locations
FOR SELECT
TO  web_user
USING (user_id = current_app_user_id());
--inserts only user_id's locations
CREATE POLICY pl_ul_insert
ON  user_features.user_locations
FOR INSERT
TO  web_user
WITH CHECK (user_id = current_app_user_id());
-- 3. UPDATE  (modify only caller’s rows AND keep owner fixed)
CREATE POLICY pl_ul_update
ON  user_features.user_locations
FOR UPDATE
TO  web_user
USING      (user_id = current_app_user_id())          -- row must already belong to caller
WITH CHECK (user_id = current_app_user_id());
--remove only caller's rows
CREATE POLICY pl_ul_delete
ON  user_features.user_locations
FOR DELETE
TO  web_user
USING (user_id = current_app_user_id());

