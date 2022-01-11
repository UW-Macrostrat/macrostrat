SELECT e.* FROM macrostrat.environs e
LEFT JOIN macrostrat.unit_environs ue
ON ue.environ_id = e.id
WHERE ue.unit_id = {unit_id};