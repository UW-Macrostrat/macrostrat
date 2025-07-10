--This query adds postgrest via views created.
--allows grant access to users
--adds policies to implement RLS for designated users.
GRANT SELECT, INSERT, UPDATE, DELETE ON
  user_features.user_locations,
  user_features.location_tags_intersect
  TO web_user;
GRANT SELECT ON user_features.location_tags TO web_user;
GRANT USAGE, SELECT ON SEQUENCE user_features.user_locations_id_seq TO web_user;

--expose tables as views so postgrest routes are created.
--CRUD ops work
CREATE OR REPLACE VIEW macrostrat_api.user_locations  AS
  SELECT * FROM user_features.user_locations;

ALTER TABLE user_features.user_locations
    ALTER COLUMN user_id SET DEFAULT current_app_user_id(),
    ALTER COLUMN user_id SET NOT NULL;
--remove user_id from view so that the column defaults to use the user_id from the jwt
CREATE OR REPLACE VIEW macrostrat_api.user_locations AS
SELECT
  id,
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



--READ ONLY
CREATE OR REPLACE VIEW macrostrat_api.location_tags  AS
  SELECT * FROM user_features.location_tags;
--CRUD ops work
CREATE OR REPLACE VIEW macrostrat_api.location_tags_intersect  AS
  SELECT * FROM user_features.location_tags_intersect;
--grant postgrest api access for the users below
GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.user_locations TO web_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.location_tags_intersect TO web_user;
--read only access to predetermined tag list
GRANT   SELECT ON macrostrat_api.location_tags TO web_user;
--ask PostgREST to pick up the view changes
NOTIFY pgrst, 'reload schema';




--create the postgrest POLICIES for the location table
ALTER TABLE user_features.user_locations ENABLE ROW LEVEL SECURITY;
CREATE POLICY pl_user_locations_all
ON user_features.user_locations
TO web_user
USING (user_id = current_app_user_id())
WITH CHECK (user_id = current_app_user_id());


--create the postgrest POLICIES for the location_tags_intersect table
ALTER TABLE user_features.location_tags_intersect ENABLE ROW LEVEL SECURITY;
CREATE POLICY pl_tag_bridge_all
ON user_features.location_tags_intersect
TO  web_user
USING      (user_id = current_app_user_id())
WITH CHECK (user_id = current_app_user_id());

