CREATE OR REPLACE VIEW macrostrat_api.saved_locations AS
SELECT *
FROM user_features.saved_locations;

GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.saved_locations TO web_anon;

NOTIFY pgrst, 'reload schema';