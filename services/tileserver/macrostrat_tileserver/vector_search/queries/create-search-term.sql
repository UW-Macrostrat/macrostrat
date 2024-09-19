INSERT INTO text_vectors.search_vector (text, model_name, model_version, text_vector)
VALUES (:text, :model_name,  :model_version, :text_vector::vector)
ON CONFLICT (text, model_name)
DO UPDATE SET text_vector = excluded.text_vector
RETURNING id;
