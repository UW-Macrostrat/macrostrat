
INSERT INTO macrostrat.places_new (place_id, name, abbrev, postal, country, country_abbrev, geom) VALUES (%(place_id)s, %(name)s, %(abbrev)s, %(postal)s, %(country)s, %(country_abbrev)s, ST_SetSRID(ST_GeomFromText(%(geom)s), 4326))

