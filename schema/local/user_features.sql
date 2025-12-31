--
-- PostgreSQL database dump
--

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

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

--
-- Name: user_features; Type: SCHEMA; Schema: -; Owner: macrostrat_admin
--

CREATE SCHEMA user_features;


ALTER SCHEMA user_features OWNER TO macrostrat_admin;

--
-- Name: current_app_role(); Type: FUNCTION; Schema: user_features; Owner: macrostrat-admin
--

CREATE FUNCTION user_features.current_app_role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'role')::text;
$$;


ALTER FUNCTION user_features.current_app_role() OWNER TO "macrostrat-admin";

--
-- Name: current_app_user_id(); Type: FUNCTION; Schema: user_features; Owner: macrostrat-admin
--

CREATE FUNCTION user_features.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int;
$$;


ALTER FUNCTION user_features.current_app_user_id() OWNER TO "macrostrat-admin";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: location_tags; Type: TABLE; Schema: user_features; Owner: macrostrat
--

CREATE TABLE user_features.location_tags (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    description text,
    color character varying(30)
);


ALTER TABLE user_features.location_tags OWNER TO macrostrat;

--
-- Name: location_tags_intersect; Type: TABLE; Schema: user_features; Owner: macrostrat
--

CREATE TABLE user_features.location_tags_intersect (
    tag_id integer NOT NULL,
    user_id integer NOT NULL,
    location_id integer NOT NULL
);


ALTER TABLE user_features.location_tags_intersect OWNER TO macrostrat;

--
-- Name: user_locations; Type: TABLE; Schema: user_features; Owner: macrostrat
--

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

--
-- Name: location_tags_id_seq; Type: SEQUENCE; Schema: user_features; Owner: macrostrat
--

CREATE SEQUENCE user_features.location_tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE user_features.location_tags_id_seq OWNER TO macrostrat;

--
-- Name: location_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: user_features; Owner: macrostrat
--

ALTER SEQUENCE user_features.location_tags_id_seq OWNED BY user_features.location_tags.id;


--
-- Name: user_locations_id_seq; Type: SEQUENCE; Schema: user_features; Owner: macrostrat
--

ALTER TABLE user_features.user_locations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME user_features.user_locations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: location_tags id; Type: DEFAULT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.location_tags ALTER COLUMN id SET DEFAULT nextval('user_features.location_tags_id_seq'::regclass);


--
-- Name: location_tags_intersect location_tags_intersect_pkey; Type: CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT location_tags_intersect_pkey PRIMARY KEY (tag_id, user_id, location_id);


--
-- Name: location_tags location_tags_pkey; Type: CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.location_tags
    ADD CONSTRAINT location_tags_pkey PRIMARY KEY (id);


--
-- Name: user_locations user_locations_pkey; Type: CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.user_locations
    ADD CONSTRAINT user_locations_pkey PRIMARY KEY (id);


--
-- Name: location_tags_intersect fk_location_id; Type: FK CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT fk_location_id FOREIGN KEY (location_id) REFERENCES user_features.user_locations(id) ON DELETE CASCADE;


--
-- Name: location_tags_intersect fk_tag_id; Type: FK CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT fk_tag_id FOREIGN KEY (tag_id) REFERENCES user_features.location_tags(id) ON DELETE CASCADE;


--
-- Name: user_locations fk_user; Type: FK CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.user_locations
    ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE CASCADE;


--
-- Name: location_tags_intersect fk_user_id; Type: FK CONSTRAINT; Schema: user_features; Owner: macrostrat
--

ALTER TABLE ONLY user_features.location_tags_intersect
    ADD CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE CASCADE;


--
-- Name: user_locations pl_ul_delete; Type: POLICY; Schema: user_features; Owner: macrostrat
--

CREATE POLICY pl_ul_delete ON user_features.user_locations FOR DELETE TO web_user, web_admin USING ((((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id())) OR (user_features.current_app_role() = 'web_admin'::text)));


--
-- Name: user_locations pl_ul_insert; Type: POLICY; Schema: user_features; Owner: macrostrat
--

CREATE POLICY pl_ul_insert ON user_features.user_locations FOR INSERT TO web_user, web_admin WITH CHECK ((((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id())) OR (user_features.current_app_role() = 'web_admin'::text)));


--
-- Name: user_locations pl_ul_select; Type: POLICY; Schema: user_features; Owner: macrostrat
--

CREATE POLICY pl_ul_select ON user_features.user_locations FOR SELECT TO web_user, web_admin USING ((((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id())) OR (user_features.current_app_role() = 'web_admin'::text)));


--
-- Name: user_locations pl_ul_update; Type: POLICY; Schema: user_features; Owner: macrostrat
--

CREATE POLICY pl_ul_update ON user_features.user_locations FOR UPDATE TO web_user, web_admin USING (((user_features.current_app_role() = 'web_user'::text) AND (user_id = user_features.current_app_user_id()))) WITH CHECK ((user_id = user_features.current_app_user_id()));


--
-- Name: user_locations; Type: ROW SECURITY; Schema: user_features; Owner: macrostrat
--

ALTER TABLE user_features.user_locations ENABLE ROW LEVEL SECURITY;

--
-- Name: TABLE user_locations; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT SELECT,DELETE ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.user_id; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(user_id),UPDATE(user_id) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.name; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(name),UPDATE(name) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.description; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(description),UPDATE(description) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.point; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(point),UPDATE(point) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.zoom; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(zoom),UPDATE(zoom) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.meters_from_point; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(meters_from_point),UPDATE(meters_from_point) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.elevation; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(elevation),UPDATE(elevation) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.azimuth; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(azimuth),UPDATE(azimuth) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.pitch; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(pitch),UPDATE(pitch) ON TABLE user_features.user_locations TO web_user;


--
-- Name: COLUMN user_locations.map_layers; Type: ACL; Schema: user_features; Owner: macrostrat
--

GRANT INSERT(map_layers),UPDATE(map_layers) ON TABLE user_features.user_locations TO web_user;


--
-- PostgreSQL database dump complete
--

