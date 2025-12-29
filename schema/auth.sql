--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: users; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS users (
    id SERIAL,
    username text NOT NULL,
    password text NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    updated_at timestamp DEFAULT now() NOT NULL,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_username_key UNIQUE (username)
);

