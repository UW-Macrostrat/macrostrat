CREATE OR REPLACE VIEW macrostrat_api.user_locations AS
SELECT *
FROM user_features.user_locations;

--this will change from web_anon to an authorized user once that workflow has been implemented.
--web_anon is used for testing only right now.
GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.user_locations TO web_anon;

NOTIFY pgrst, 'reload schema';