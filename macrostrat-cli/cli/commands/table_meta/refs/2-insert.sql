
INSERT INTO macrostrat.refs_new (id, pub_year, author, ref, doi, compilation_code, url, rgeom) VALUES (%(id)s, %(pub_year)s, %(author)s, %(ref)s, %(doi)s, %(compilation_code)s, %(url)s, ST_SetSRID(ST_GeomFromText(%(rgeom)s), 4326))

