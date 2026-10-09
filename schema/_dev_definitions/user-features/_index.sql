-- @subsystem: user-features
-- @depends-on: macrostrat-api
-- Saved user locations, their tags, and the API views over them. Development only.



SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA user_features;

CREATE FUNCTION user_features.current_app_role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'role')::text;
$$;

SET check_function_bodies = off;
CREATE OR REPLACE FUNCTION user_features.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog
    AS $$
  SELECT id
  FROM macrostrat_auth."user"
  WHERE sub = current_setting('request.jwt.claims', true)::json ->> 'sub';
$$;
SET check_function_bodies = on;
ALTER FUNCTION user_features.current_app_user_id() OWNER TO macrostrat;
GRANT EXECUTE ON FUNCTION user_features.current_app_user_id() TO web_anon, web_user, web_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE user_features.location_tags (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    description text,
    color character varying(30)
);

CREATE TABLE user_features.location_tags_intersect (
    tag_id integer NOT NULL,
    user_id integer NOT NULL,
    location_id integer NOT NULL
);

CREATE TABLE user_features.user_locations (
    id integer NOT NULL,
    user_id integer,
    name character varying(120) NOT NULL,
    description text,
    point public.geometry(Point,4326),
    zoom numeric,
    meters_from_point numeric,
    elevation numeric,
    azimuth numeric,
    pitch numeric,
    map_layers text[],
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE user_features.location_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE user_features.location_tags_id_seq OWNED BY user_features.location_tags.id;

ALTER TABLE user_features.user_locations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME user_features.user_locations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE ONLY user_features.location_tags ALTER COLUMN id SET DEFAULT nextval('user_features.location_tags_id_seq'::regclass);

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT location_tags_intersect_pkey PRIMARY KEY (tag_id, user_id, location_id);

ALTER TABLE ONLY user_features.location_tags
    ADD CONSTRAINT location_tags_pkey PRIMARY KEY (id);

-- The tag list users pick from; API users can only read it
INSERT INTO user_features.location_tags (id, name, description, color) VALUES
  (1, 'Basalt Outcrop', 'Exposure of dark, fine‑grained basaltic lava', '#4B4E6D'),
  (2, 'Fossil Locality', 'Site where macro‑ or microfossils have been collected', '#C19A6B'),
  (3, 'Fault Trace', 'Mapped surface expression of a fault plane', '#FF6F61'),
  (4, 'Glacial Erratic', 'Large exotic boulder deposited by glacial ice', '#3DA5D9'),
  (5, 'Mineral Prospect', 'Area under evaluation for economic mineralization', '#FFD166'),
  (6, 'Stratotype Section', 'Formally designated reference stratigraphic section', '#6D8B74'),
  (7, 'Core Sample Site', 'Location where drill‑core was extracted', '#8E7DBE'),
  (8, 'Hydrothermal Vent', 'Vent or fissure of hydrothermal fluids (active/pale)', '#E9724C'),
  (9, 'Paleosol Horizon', 'Profile of an ancient soil preserved in the rock record', '#A67C52'),
  (10, 'Dike Intrusion', 'Tabular igneous body cutting host strata', '#FFB3BA')
ON CONFLICT DO NOTHING;

SELECT setval('user_features.location_tags_id_seq', (SELECT max(id) FROM user_features.location_tags));

ALTER TABLE ONLY user_features.user_locations
    ADD CONSTRAINT user_locations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT fk_location_id FOREIGN KEY (location_id) REFERENCES user_features.user_locations(id) ON DELETE CASCADE;

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT fk_tag_id FOREIGN KEY (tag_id) REFERENCES user_features.location_tags(id) ON DELETE CASCADE;

ALTER TABLE ONLY user_features.user_locations
    ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE CASCADE;

-- A saved location belongs to the account that made it, whatever tier that
-- account holds (web_user, web_authorized, ...); an administrator sees and
-- manages all of them. Ownership is the test, not the role name: an earlier
-- version compared the role to 'web_user' literally, which would have locked
-- an authorized user out of their own locations. `TO web_user, web_admin`
-- reaches every tier, since each is a member of web_user.
CREATE POLICY pl_ul_select ON user_features.user_locations FOR SELECT TO web_user, web_admin
    USING (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

CREATE POLICY pl_ul_insert ON user_features.user_locations FOR INSERT TO web_user, web_admin
    WITH CHECK (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

CREATE POLICY pl_ul_update ON user_features.user_locations FOR UPDATE TO web_user, web_admin
    USING (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin')
    WITH CHECK (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

CREATE POLICY pl_ul_delete ON user_features.user_locations FOR DELETE TO web_user, web_admin
    USING (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

ALTER TABLE user_features.user_locations ENABLE ROW LEVEL SECURITY;

-- The tag links are owned the same way. Without this, any signed-in user could
-- tag or untag anyone's locations through the macrostrat_api view.
CREATE POLICY pl_lti_select ON user_features.location_tags_intersect FOR SELECT TO web_user, web_admin
    USING (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

CREATE POLICY pl_lti_insert ON user_features.location_tags_intersect FOR INSERT TO web_user, web_admin
    WITH CHECK (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

CREATE POLICY pl_lti_update ON user_features.location_tags_intersect FOR UPDATE TO web_user, web_admin
    USING (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin')
    WITH CHECK (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

CREATE POLICY pl_lti_delete ON user_features.location_tags_intersect FOR DELETE TO web_user, web_admin
    USING (user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin');

ALTER TABLE user_features.location_tags_intersect ENABLE ROW LEVEL SECURITY;

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE user_features.location_tags_intersect TO web_user, web_admin;

GRANT SELECT,DELETE ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(user_id),UPDATE(user_id) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(name),UPDATE(name) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(description),UPDATE(description) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(point),UPDATE(point) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(zoom),UPDATE(zoom) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(meters_from_point),UPDATE(meters_from_point) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(elevation),UPDATE(elevation) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(azimuth),UPDATE(azimuth) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(pitch),UPDATE(pitch) ON TABLE user_features.user_locations TO web_user;

GRANT INSERT(map_layers),UPDATE(map_layers) ON TABLE user_features.user_locations TO web_user;

