/* A base query for units */

SELECT u.*, l.interval_name name_fo, i.interval_name name_lo  FROM macrostrat.units u
LEFT JOIN macrostrat.intervals l
ON u.fo = l.id
LEFT JOIN macrostrat.intervals i
ON u.lo = i.id;