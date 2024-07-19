/* Remove old and unused columns from tables */

ALTER TABLE macrostrat.units 
DROP COLUMN fo_h,
DROP COLUMN lo_h;