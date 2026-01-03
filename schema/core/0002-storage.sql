
CREATE SCHEMA storage;
ALTER SCHEMA storage OWNER TO macrostrat;

CREATE TYPE storage.scheme AS ENUM (
    's3',
    'https',
    'http'
);
ALTER TYPE storage.scheme OWNER TO macrostrat;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE storage.object (
    id integer NOT NULL,
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
ALTER TABLE storage.object_id_seq OWNER TO macrostrat;

ALTER SEQUENCE storage.object_id_seq OWNED BY storage.object.id;

ALTER TABLE ONLY storage.object ALTER COLUMN id SET DEFAULT nextval('storage.object_id_seq'::regclass);

ALTER TABLE ONLY storage.object
    ADD CONSTRAINT object_pkey PRIMARY KEY (id);

ALTER TABLE ONLY storage.object
    ADD CONSTRAINT unique_file UNIQUE (scheme, host, bucket, key);

