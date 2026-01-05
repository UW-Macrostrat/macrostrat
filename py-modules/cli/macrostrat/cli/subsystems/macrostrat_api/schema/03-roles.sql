/** Function to check the current role that PostgREST is using */

CREATE OR REPLACE FUNCTION macrostrat_api.auth_status() RETURNS jsonb AS $$
  SELECT jsonb_build_object(
    'token', current_setting('request.jwt.claims', true)::jsonb,
    'role', current_user
  );
$$ LANGUAGE SQL;
