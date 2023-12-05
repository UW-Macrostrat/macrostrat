--
-- PostgreSQL User database dump
--

--
-- Name: user; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA "macrostrat_auth";
ALTER SCHEMA "macrostrat_auth" OWNER TO macrostrat;

--
-- Name: group; Type: TABLE; Schema: user; Owner: macrostrat
--

CREATE TABLE "macrostrat_auth"."group" (
    id SERIAL NOT NULL primary key,
    name character varying(255) NOT NULL
);
ALTER TABLE "macrostrat_auth"."group" OWNER TO macrostrat;



--
-- Name: user; Type: TABLE; Schema: user; Owner: macrostrat
--

/** A user table designed for use with OpenID */
CREATE TABLE "macrostrat_auth"."user" (
    id SERIAL NOT NULL primary key,
    -- Subject Identifier
    -- https://openid.net/specs/openid-connect-core-1_0.html#IDToken
    sub character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL
);
ALTER SEQUENCE "macrostrat_auth".user_id_seq OWNER TO macrostrat;

-- Create a trigger function --
CREATE OR REPLACE FUNCTION update_updated_on()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_on = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE "macrostrat_auth"."user" OWNER TO macrostrat;

-- Trigger function on row change --
CREATE TRIGGER update_updated_on_trigger
BEFORE UPDATE ON "macrostrat_auth"."user"
FOR EACH ROW
WHEN (OLD IS DISTINCT FROM NEW)
EXECUTE FUNCTION update_updated_on();

--
-- Name: group_id_seq; Type: SEQUENCE; Schema: user; Owner: macrostrat
--


CREATE TABLE "macrostrat_auth".group_members (
    id SERIAL NOT NULL primary key,
    group_id integer NOT NULL references "macrostrat_auth"."group"(id),
    user_id integer NOT NULL references "macrostrat_auth"."user"(id)
);
ALTER TABLE "macrostrat_auth".group_members OWNER TO macrostrat;

DROP TRIGGER IF EXISTS update_last_updated_trigger ON "macrostrat_auth"."user"
