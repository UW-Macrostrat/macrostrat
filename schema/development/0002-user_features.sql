

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA user_features;
ALTER SCHEMA user_features OWNER TO macrostrat_admin;

CREATE FUNCTION user_features.current_app_role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'role')::text;
$$;
ALTER FUNCTION user_features.current_app_role() OWNER TO "macrostrat-admin";

CREATE FUNCTION user_features.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int;
$$;
ALTER FUNCTION user_features.current_app_user_id() OWNER TO "macrostrat-admin";
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE user_features.location_tags (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    description text,
    color character varying(30)
);
ALTER TABLE user_features.location_tags OWNER TO macrostrat;

CREATE TABLE user_features.location_tags_intersect (
    tag_id integer NOT NULL,
    user_id integer NOT NULL,
    location_id integer NOT NULL
);
ALTER TABLE user_features.location_tags_intersect OWNER TO macrostrat;

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
ALTER TABLE user_features.user_locations OWNER TO macrostrat;

CREATE SEQUENCE user_features.location_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE user_features.location_tags_id_seq OWNER TO macrostrat;

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

CREATE POLICY pl_ul_delete ON user_features.user_locations FOR DELETE TO web_user, web_admin USING ((((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id())) OR (user_features.current_app_role() = 'web_admin'::text)));

CREATE POLICY pl_ul_insert ON user_features.user_locations FOR INSERT TO web_user, web_admin WITH CHECK ((((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id())) OR (user_features.current_app_role() = 'web_admin'::text)));

CREATE POLICY pl_ul_select ON user_features.user_locations FOR SELECT TO web_user, web_admin USING ((((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id())) OR (user_features.current_app_role() = 'web_admin'::text)));

CREATE POLICY pl_ul_update ON user_features.user_locations FOR UPDATE TO web_user, web_admin USING (((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id()))) WITH CHECK ((user_id = user_features.current_app_user_id()));

ALTER TABLE user_features.user_locations ENABLE ROW LEVEL SECURITY;

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

