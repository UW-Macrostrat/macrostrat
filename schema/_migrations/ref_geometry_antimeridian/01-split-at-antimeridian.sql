/* A ring with vertices written on both sides of 180° sweeps the globe and
   crosses itself (the GNS lexicon's New Zealand outline covered Patagonia).
   Shift into 0-360, where it is valid, then split back at the antimeridian. */
UPDATE macrostrat.refs
SET rgeom = ST_WrapX(ST_ShiftLongitude(rgeom), 180, -360)
WHERE NOT ST_IsValid(rgeom)
  AND ST_XMax(rgeom) - ST_XMin(rgeom) > 180
  AND ST_IsValid(ST_ShiftLongitude(rgeom));
