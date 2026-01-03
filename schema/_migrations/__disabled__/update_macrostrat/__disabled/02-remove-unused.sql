/* Remove old and unused columns from tables */

ALTER TABLE macrostrat.units
DROP COLUMN IF EXISTS fo_h CASCADE,
DROP COLUMN IF EXISTS lo_h CASCADE;
