BEGIN;
CREATE OR REPLACE FUNCTION text_vectors.distance(
    text_vector vector,
    search_vector vector
) RETURNS float
AS $$
BEGIN
    RETURN 1 - (text_vector <=> search_vector);
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION text_vectors.norm_distance(
    text_vector vector,
    search_vector vector
) RETURNS float
AS $$
BEGIN
    RETURN -(text_vector <#> search_vector);
END;
$$ LANGUAGE plpgsql;

TRUNCATE TABLE text_vectors.search_vector;
COMMIT;
END;
