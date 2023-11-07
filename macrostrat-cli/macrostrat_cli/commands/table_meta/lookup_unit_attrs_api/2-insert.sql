
INSERT INTO macrostrat.lookup_unit_attrs_api_new (unit_id, lith, environ, econ, measure_short, measure_long) VALUES 
(%(unit_id)s, encode(%(lith)s, 'escape')::json, encode(%(environ)s, 'escape')::json, encode(%(econ)s, 'escape')::json, encode(%(measure_short)s, 'escape')::json, encode(%(measure_long)s, 'escape')::json)

