
INSERT INTO macrostrat.pbdb_collections_new (collection_no, name, early_age, late_age, grp, formation, member, lithologies, environment, reference_no, n_occs, geom) VALUES (%(collection_no)s, regexp_replace(regexp_replace(replace(%(collection_name)s, '"', ''), '\(\.*\)', ''), '\s+$', ''), %(early_age)s, %(late_age)s, regexp_replace(regexp_replace(replace(replace(%(grp)s, '.', ''), '"', ''), '\(\.*\)', ''), '\s+$', ''), regexp_replace(regexp_replace(replace(replace(%(formation)s, '.', ''), '"', ''), '\(\.*\)', ''), '\s+$', ''), regexp_replace(regexp_replace(replace(replace(%(member)s, '.', ''), '"', ''), '\(\.*\)', ''), '\s+$', ''), string_to_array(replace(%(lithology)s, '"', ''), '/'), %(environment)s, %(reference_no)s, %(n_occs)s, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326))
