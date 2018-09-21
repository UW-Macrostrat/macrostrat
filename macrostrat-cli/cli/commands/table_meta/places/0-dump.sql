
SELECT place_id, name, abbrev, postal, country, country_abbrev, ST_AsText(geom) geom
FROM places

