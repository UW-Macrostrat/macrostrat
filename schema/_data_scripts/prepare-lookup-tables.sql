SELECT map_id FROM lookup_medium
GROUP BY map_id
HAVING COUNT(*) > 1;

DELETE FROM lookup_tiny a
  USING lookup_tiny b
WHERE a.ctid < b.ctid
  AND a.map_id = b.map_id;

DELETE FROM lookup_small a
  USING lookup_small b
WHERE a.ctid < b.ctid
  AND a.map_id = b.map_id;

DELETE FROM lookup_medium a
  USING lookup_medium b
WHERE a.ctid < b.ctid
  AND a.map_id = b.map_id;

DELETE FROM lookup_large a
  USING lookup_large b
WHERE a.ctid < b.ctid
  AND a.map_id = b.map_id;
