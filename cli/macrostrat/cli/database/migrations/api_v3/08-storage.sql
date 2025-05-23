CREATE SCHEMA IF NOT EXISTS storage;

CREATE TABLE storage.object_group (
    id serial primary key
);

ALTER TABLE storage.object_group OWNER TO macrostrat;

CREATE TYPE storage.scheme AS ENUM (
    's3',
    'https'
);

ALTER TYPE storage.scheme OWNER TO macrostrat;

CREATE TABLE IF NOT EXISTS storage.object (
    id integer NOT NULL,
    object_group_id integer references storage.object_group(id) ON DELETE CASCADE,
    scheme storage.scheme NOT NULL,
    host character varying(255) NOT NULL,
    bucket character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
    source jsonb,
    mime_type character varying(255),
    sha256_hash character varying(255),
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL,
    deleted_on timestamp with time zone
);

ALTER TABLE storage.object OWNER TO macrostrat;

CREATE SEQUENCE storage.object_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE storage.object_id_seq OWNER TO macrostrat;

ALTER SEQUENCE storage.object_id_seq OWNED BY storage.object.id;

GRANT ALL ON DATABASE macrostrat TO postgrest;

--give macrostrat user SELECT and INSERT on all tables in the storage schema
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA storage TO macrostrat;
GRANT USAGE ON SCHEMA storage TO macrostrat;


