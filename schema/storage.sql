--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: scheme; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE scheme AS ENUM (
    's3',
    'https',
    'http'
);

--
-- Name: object; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS object (
    id SERIAL,
    scheme scheme NOT NULL,
    host varchar(255) NOT NULL,
    bucket varchar(255) NOT NULL,
    key varchar(255) NOT NULL,
    source jsonb,
    mime_type varchar(255),
    sha256_hash varchar(255),
    created_on timestamptz DEFAULT now() NOT NULL,
    updated_on timestamptz DEFAULT now() NOT NULL,
    deleted_on timestamptz,
    CONSTRAINT object_pkey PRIMARY KEY (id),
    CONSTRAINT unique_file UNIQUE (scheme, host, bucket, key)
);

