--This query adds postgrest via views created.
--allows grant access to users
--adds policies to implement RLS for designated users.

--expose tables as views so postgrest routes are created.
--CRUD ops work
--remove user_id from view so that the column defaults to use the user_id from the jwt
--removed id from the view so that it autoincrements rather than HTTP posts having to handle that value

CREATE OR REPLACE VIEW macrostrat_api.test_helper_functions  AS
  SELECT current_app_role(), current_app_user_id();

--Ensures HTTP's require a parameter to delete or update rows. Bulk deletions and bulk updates are not allowed.
CREATE EXTENSION IF NOT EXISTS pg_safe_update;
SELECT pg_safe_update.enable();



CREATE OR REPLACE VIEW macrostrat_api.user_locations_view
--these security options ensures that the view inherits the user's role requesting data from http
WITH (security_invoker = true)
  AS
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
GRANT SELECT ON macrostrat_api.user_locations_view TO web_user, web_admin;
--grant insert,update,delete only on mutable columns
GRANT INSERT (user_id, name, description, point, zoom,
              meters_from_point, elevation, azimuth,
              pitch, map_layers) ON macrostrat_api.user_locations_view TO web_user, web_admin;
GRANT UPDATE (id, user_id, name, description, point, zoom,
              meters_from_point, elevation, azimuth,
              pitch, map_layers) ON macrostrat_api.user_locations_view TO web_user, web_admin;
GRANT DELETE ON macrostrat_api.user_locations_view TO web_user, web_admin;



--READ ONLY
CREATE OR REPLACE VIEW macrostrat_api.location_tags  AS
  SELECT * FROM user_features.location_tags;
--CRUD ops work
CREATE OR REPLACE VIEW macrostrat_api.location_tags_intersect  AS
  SELECT * FROM user_features.location_tags_intersect;


GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.location_tags_intersect TO web_user, web_admin;
--read only access to predetermined tag list
GRANT SELECT ON macrostrat_api.location_tags TO web_user, web_admin;
--ask PostgREST to pick up the view changes
NOTIFY pgrst, 'reload schema';


--create the postgrest POLICIES for the location table
ALTER TABLE user_features.user_locations ENABLE ROW LEVEL SECURITY;
--selects only user_id's locations
DROP POLICY IF EXISTS pl_ul_select ON user_features.user_locations;

CREATE POLICY pl_ul_select
ON  user_features.user_locations
FOR SELECT
TO web_admin, web_user
USING (
    /* If the JWT role is exactly 'web_user', show only own rows … */
    ( current_app_role() = 'web_user'
      AND user_id = current_app_user_id() )
    /* …Otherwise if web_admin show everything */
    OR ( current_app_role() = 'web_admin' )
);

--policy for INSERTS
DROP POLICY IF EXISTS pl_ul_insert ON user_features.user_locations;
CREATE POLICY pl_ul_insert
ON user_features.user_locations
FOR INSERT
TO web_user, web_admin
WITH CHECK (    (current_app_role() = 'web_user'
      AND user_id = current_app_user_id())
      OR current_app_role() = 'web_admin'
);


-- 3. UPDATE  (modify only caller’s rows AND keep owner fixed)
DROP POLICY IF EXISTS pl_ul_update ON  user_features.user_locations;

CREATE POLICY pl_ul_update
ON  user_features.user_locations
FOR UPDATE
TO  web_user, web_admin
USING (current_app_role() = 'web_user' AND user_id = current_app_user_id())
WITH CHECK (user_id = current_app_user_id());
--remove only caller's rows

DROP POLICY IF EXISTS pl_ul_delete ON  user_features.user_locations;
CREATE POLICY pl_ul_delete
ON  user_features.user_locations
FOR DELETE
TO  web_user, web_admin
USING (
    ( current_app_role() = 'web_user'
      AND user_id = current_app_user_id() )
    OR ( current_app_role() = 'web_admin' )
);

--view policies

SELECT *
FROM   pg_policies
WHERE  schemaname = 'user_features'
  AND  tablename  = 'user_locations';
NOTIFY pgrst, 'reload schema';



