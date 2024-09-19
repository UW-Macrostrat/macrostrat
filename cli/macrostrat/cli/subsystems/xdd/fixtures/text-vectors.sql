CREATE SCHEMA IF NOT EXISTS text_vectors;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS text_vectors.search_vector (
    text text NOT NULL,
    model text NOT NULL,
    text_vector vector NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY (text, model)
);
