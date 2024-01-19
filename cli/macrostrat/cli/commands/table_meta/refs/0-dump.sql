
SELECT id, pub_year, author, ref, doi, compilation_code, url, ST_AsText(rgeom) rgeom
FROM refs

