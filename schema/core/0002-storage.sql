
CREATE SCHEMA storage;

CREATE TYPE storage.scheme AS ENUM (
    's3',
    'https',
    'http'
);

CREATE TABLE storage.objects (
    id integer generated always as identity primary key,
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


ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT unique_file UNIQUE (scheme, host, bucket, key);

