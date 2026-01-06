SELECT
  s.sample_id,
  ST_SetSRID(ST_MakePoint(st.long_dec, st.lat_dec), 4326) AS geom,
  ia.interpreted_age
FROM sample s
JOIN collecting_event ce ON s.coll_event_id = ce.coll_event_id
JOIN site st ON st.site_id = ce.site_id
JOIN interpreted_age ia ON ia.sample_id = s.sample_id
WHERE NOT s.is_standard
ORDER BY s.sample_id
