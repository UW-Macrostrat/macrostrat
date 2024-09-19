CREATE SCHEMA IF NOT EXISTS text_vectors;

-- Allow the xdd-writer role full control of the text_vectors schema
GRANT USAGE ON SCHEMA text_vectors TO "xdd-writer";
GRANT ALL ON SCHEMA text_vectors TO "xdd-writer";

GRANT USAGE ON SCHEMA macrostrat TO "xdd-writer";
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO "xdd-writer";
GRANT USAGE ON SCHEMA maps TO "xdd-writer";
GRANT SELECT ON ALL TABLES IN SCHEMA maps TO "xdd-writer";
