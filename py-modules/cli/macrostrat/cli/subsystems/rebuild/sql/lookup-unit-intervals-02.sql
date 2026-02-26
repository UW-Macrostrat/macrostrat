UPDATE lookup_unit_intervals_new
SET period = concat_WS('-',fo_period,lo_period)
where period = '' and fo_period not like '';

UPDATE lookup_unit_intervals_new set period = eon where period = '' and eon = 'Archean';

UPDATE lookup_unit_intervals_new set period = concat_WS('-', fo_interval, lo_period) where fo_interval = 'Archean';

UPDATE lookup_unit_intervals_new set period = 'Precambrian' where period = '' and t_age >= 541;

/** Note: this query was rescued from the 'schlep' migration process and was not part of old mariadb update script
 */
UPDATE lookup_unit_intervals_new lui
SET best_interval_id = CASE
  WHEN age_id > 0 THEN
   age_id
  WHEN epoch_id > 0 THEN
   epoch_id
  WHEN period_id > 0 THEN
   period_id
  WHEN era_id > 0 THEN
   era_id
  WHEN eon_id > 0 THEN
   eon_id
  ELSE
   0
  END;
