UPDATE lookup_units_new
SET period = eon
WHERE period = '' AND eon = 'Archean';

UPDATE lookup_units_new
SET period = 'Precambrian'
WHERE period = '' AND t_age >= 541;

/** Set periods in special cases where the unit spans several periods */
UPDATE lookup_units_new
SET period = concat_WS('-', (
        SELECT intervals.interval_name
        FROM intervals
        JOIN timescales_intervals ON intervals.id = interval_id
        JOIN timescales on timescale_id = timescales.id
        WHERE timescale = 'international periods'
        AND age_top <= (SELECT age_top FROM intervals WHERE id = b_int)
        AND age_bottom >= (SELECT age_bottom FROM intervals WHERE id = b_int)
    ), (
        SELECT intervals.interval_name
        FROM intervals
        JOIN timescales_intervals ON intervals.id = interval_id
        JOIN timescales on timescale_id = timescales.id
        WHERE timescale = 'international periods'
        AND age_top <= (SELECT age_top FROM intervals WHERE id = t_int)
        AND age_bottom >= (SELECT age_bottom FROM intervals WHERE id = t_int)
    ))
WHERE period = '';


