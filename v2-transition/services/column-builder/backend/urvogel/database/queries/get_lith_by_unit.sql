SELECT l.* FROM macrostrat.liths l
LEFT JOIN macrostrat.unit_liths ul
ON ul.lith_id = l.id
WHERE ul.unit_id = {unit_id};